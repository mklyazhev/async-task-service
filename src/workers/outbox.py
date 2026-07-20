import asyncio
import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_, select

from src.broker import TASKS_EXCHANGE, TASKS_QUEUE, broker
from src.common.config import get_settings
from src.common.enums import OutboxStatus, TaskStatus
from src.db.engine import async_session_maker
from src.db.models.outbox import OutboxEvent
from src.db.models.task import Task

logger = logging.getLogger(__name__)


async def claim_events() -> list[UUID]:
    now = datetime.now(timezone.utc)
    stale_lock = now - timedelta(minutes=1)
    async with async_session_maker() as session, session.begin():
        events = (await session.execute(
            select(OutboxEvent)
            .where(
                or_(
                    OutboxEvent.status.in_([OutboxStatus.NEW, OutboxStatus.RETRY]),
                    (OutboxEvent.status == OutboxStatus.PROCESSING) & (OutboxEvent.locked_at < stale_lock),
                ),
            )
            .where(
                or_(
                    OutboxEvent.next_retry_at.is_(None),
                    OutboxEvent.next_retry_at <= now,
                ),
            )
            .order_by(OutboxEvent.created_at)
            .with_for_update(skip_locked=True)
            .limit(get_settings().outbox_batch_size)
        )).scalars().all()
        for event in events:
            event.status = OutboxStatus.PROCESSING
            event.locked_at = now
        return [event.id for event in events]


async def publish_event(event_id: UUID) -> None:
    try:
        async with async_session_maker() as session:
            event = await session.get(OutboxEvent, event_id)
            if not event or event.status != OutboxStatus.PROCESSING:
                return
            await broker.publish(
                event.payload,
                queue=TASKS_QUEUE,
                exchange=TASKS_EXCHANGE,
                priority=event.priority,
                persist=True,
                message_id=str(event.id),
            )
        async with async_session_maker() as session, session.begin():
            event = await session.get(OutboxEvent, event_id, with_for_update=True)
            if not event:
                return
            event.status = OutboxStatus.PUBLISHED
            event.published_at = datetime.now(timezone.utc)
            task = await session.get(
                Task,
                UUID(event.payload["task_id"]),
                with_for_update=True,
            )
            if task and task.status == TaskStatus.NEW:
                task.status = TaskStatus.PENDING
    except Exception as exc:
        async with async_session_maker() as session, session.begin():
            event = await session.get(OutboxEvent, event_id, with_for_update=True)
            if event:
                event.attempts += 1
                event.status = OutboxStatus.RETRY
                event.last_error = str(exc)[:1000]
                event.next_retry_at = datetime.now(timezone.utc) + timedelta(
                    seconds=min(60, 2 ** event.attempts),
                )
        logger.exception("Could not publish outbox event %s", event_id)


async def run() -> None:
    await broker.connect()
    try:
        while True:
            for event_id in await claim_events():
                await publish_event(event_id)
            await asyncio.sleep(get_settings().outbox_poll_interval_seconds)
    finally:
        await broker.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
