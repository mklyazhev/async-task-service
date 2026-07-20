from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from src.common.enums import TaskPriority, TaskStatus
from src.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_task_returns_accepted() -> None:
    task = type(
        "TaskStub",
        (),
        {
            "id": uuid4(),
            "status": TaskStatus.NEW,
            "created_at": datetime.now(timezone.utc),
        },
    )()
    with patch(
        "src.api.v1.tasks.TaskService.create",
        new_callable=AsyncMock,
        return_value=task,
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/tasks",
                json={"title": "Report", "description": "Build report", "priority": "HIGH"},
            )
    assert response.status_code == 202
    assert response.json()["status"] == "NEW"


@pytest.mark.asyncio
async def test_list_validates_pagination() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/tasks?page=0")
    assert response.status_code == 422


def test_priority_is_textual_api_value() -> None:
    assert TaskPriority.HIGH.value == "HIGH"
    assert TaskPriority.HIGH.rabbit_priority == 3
