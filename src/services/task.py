from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import OutboxStatus, TaskPriority, TaskStatus
from src.db.models.outbox import OutboxEvent
from src.db.models.task import Task
from src.repositories.task import TaskRepository
from src.schemas.task import TaskCreate
from src.db.engine import get_session

EVENT_TASK_CREATED = "task.created"


class TaskNotFoundError(Exception):
    pass


class TaskCancellationError(Exception):
    pass


class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = TaskRepository(session)

    async def create(self, data: TaskCreate) -> Task:
        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            status=TaskStatus.NEW,
        )
        self.session.add(task)
        await self.session.flush()
        self.session.add(OutboxEvent(
                event_type=EVENT_TASK_CREATED,
                payload={"task_id": str(task.id)},
                priority=data.priority.rabbit_priority,
                status=OutboxStatus.NEW,
            ),
        )
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def get(self, task_id: UUID) -> Task:
        task = await self.repository.get(task_id)
        if not task:
            raise TaskNotFoundError
        return task

    async def list(
        self,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        return await self.repository.list(status, priority, page, page_size)

    async def cancel(self, task_id: UUID) -> Task:
        async with self.session.begin():
            task = await self.repository.get(task_id, lock=True)
            if not task:
                raise TaskNotFoundError
            if task.status not in {TaskStatus.NEW, TaskStatus.PENDING}:
                raise TaskCancellationError(
                    f"Task in {task.status} cannot be cancelled",
                )
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now(timezone.utc)
        return task


def get_task_service(session: AsyncSession = Depends(get_session)) -> TaskService:
    return TaskService(session)
