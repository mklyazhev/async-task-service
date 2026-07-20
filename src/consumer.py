import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from faststream import FastStream
from sqlalchemy import select

from src.broker import TASKS_EXCHANGE, TASKS_QUEUE, broker
from src.common.enums import TaskStatus
from src.db.engine import async_session_maker
from src.db.models.task import Task
from src.services.executor import TaskExecutor

logger = logging.getLogger(__name__)
app = FastStream(broker)
executor = TaskExecutor()


@broker.subscriber(TASKS_QUEUE, exchange=TASKS_EXCHANGE)
async def handle_task(payload: dict) -> None:
    task_id = UUID(payload["task_id"])
    async with async_session_maker() as session, session.begin():
        task = (
            await session.execute(
                select(Task).where(Task.id == task_id).with_for_update(),
            )
        ).scalar_one_or_none()
        if not task or task.status in {
            TaskStatus.CANCELLED,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        }:
            return
        if task.status == TaskStatus.IN_PROGRESS:
            return
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now(timezone.utc)

    try:
        async with async_session_maker() as session:
            task = await session.get(Task, task_id)
            if not task:
                return
            result = await executor.execute(task)
        async with async_session_maker() as session, session.begin():
            task = await session.get(Task, task_id, with_for_update=True)
            if task and task.status == TaskStatus.IN_PROGRESS:
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now(timezone.utc)
    except Exception as exc:
        async with async_session_maker() as session, session.begin():
            task = await session.get(Task, task_id, with_for_update=True)
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = str(exc)[:1000]
                task.completed_at = datetime.now(timezone.utc)
        logger.exception("Task %s failed", task_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(app.run())
