import asyncio

from src.common.config import get_settings
from src.db.models.task import Task


class TaskExecutor:
    async def execute(self, task: Task) -> dict:
        await asyncio.sleep(get_settings().task_execution_seconds)
        if task.title.lower().startswith("fail:"):  # Ветка для обработки FAILED
            raise RuntimeError("Execution was intentionally failed by task title")
        return {"message": "Task completed", "task_id": str(task.id)}
