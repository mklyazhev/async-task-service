from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.enums import TaskPriority, TaskStatus
from src.db.models.task import Task


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, task_id: UUID, *, lock: bool = False) -> Task | None:
        statement = select(Task).where(Task.id == task_id)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def list(
        self,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        filters = []
        if status:
            filters.append(Task.status == status)
        if priority:
            filters.append(Task.priority == priority)
        statement = (
            select(Task)
            .where(*filters)
            .order_by(
                Task.priority.desc(),
                Task.created_at.desc(),
            )
        )
        tasks = (
            (
                await self.session.execute(
                    statement.offset((page - 1) * page_size).limit(page_size),
                )
            )
            .scalars()
            .all()
        )
        total = await self.session.scalar(
            select(func.count()).select_from(Task).where(*filters),
        )
        return tasks, total or 0
