import pytest

from src.db.models.task import Task
from src.common.enums import TaskPriority, TaskStatus
from src.services.executor import TaskExecutor


@pytest.mark.asyncio
async def test_executor_returns_result() -> None:
    task = Task(
        title="report",
        description="generate",
        priority=TaskPriority.HIGH,
        status=TaskStatus.IN_PROGRESS,
    )
    result = await TaskExecutor().execute(task)
    assert result["message"] == "Task completed"


@pytest.mark.asyncio
async def test_executor_marks_intentional_failure() -> None:
    task = Task(
        title="fail: report",
        description="generate",
        priority=TaskPriority.LOW,
        status=TaskStatus.IN_PROGRESS,
    )
    with pytest.raises(RuntimeError, match="intentionally"):
        await TaskExecutor().execute(task)
