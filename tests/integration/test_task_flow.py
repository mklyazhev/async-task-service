import asyncio
import os
import time
from uuid import uuid4

import httpx
import pytest

API_URL = os.getenv("INTEGRATION_API_URL", "http://localhost:8000").rstrip("/")
RUN_INTEGRATION = os.getenv("RUN_INTEGRATION") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not RUN_INTEGRATION,
        reason="Set RUN_INTEGRATION=1 after docker compose is running",
    ),
]


async def wait_for_status(
    client: httpx.AsyncClient,
    task_id: str,
    expected_status: str,
    timeout_seconds: float = 15,
) -> dict:
    deadline = time.monotonic() + timeout_seconds
    last_task: dict = {}

    while time.monotonic() < deadline:
        response = await client.get(f"/api/v1/tasks/{task_id}")
        response.raise_for_status()
        last_task = response.json()
        if last_task["status"] == expected_status:
            return last_task
        if last_task["status"] == "FAILED":
            pytest.fail(f"Task failed: {last_task['error_message']}")
        await asyncio.sleep(0.25)

    pytest.fail(
        f"Task {task_id} did not reach {expected_status}; last state: {last_task}",
    )


@pytest.mark.asyncio
async def test_task_is_processed_end_to_end() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"integration-{uuid4()}",
                "description": "Verifies API, PostgreSQL, outbox, RabbitMQ and consumer.",
                "priority": "HIGH",
            },
        )

        assert response.status_code == 202
        created_task = response.json()
        assert created_task["status"] == "NEW"

        completed_task = await wait_for_status(
            client,
            created_task["id"],
            "COMPLETED",
        )

        assert completed_task["result"]["message"] == "Task completed"
        assert completed_task["started_at"] is not None
        assert completed_task["completed_at"] is not None

        list_response = await client.get(
            "/api/v1/tasks",
            params={"status": "COMPLETED", "priority": "HIGH"},
        )
        assert list_response.status_code == 200
        assert created_task["id"] in {
            task["id"] for task in list_response.json()["items"]
        }


@pytest.mark.asyncio
async def test_pending_task_can_be_cancelled() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"cancel-integration-{uuid4()}",
                "description": "Verifies cancellation before a consumer starts execution.",
                "priority": "LOW",
            },
        )
        assert response.status_code == 202
        task_id = response.json()["id"]

        cancel_response = await client.delete(f"/api/v1/tasks/{task_id}")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "CANCELLED"

        task_response = await client.get(f"/api/v1/tasks/{task_id}")
        assert task_response.status_code == 200
        assert task_response.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_failed_task_contains_error_message() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"fail: integration-{uuid4()}",
                "description": "Verifies the FAILED status and persisted error message.",
                "priority": "MEDIUM",
            },
        )
        assert response.status_code == 202

        failed_task = await wait_for_status(
            client,
            response.json()["id"],
            "FAILED",
        )
        assert failed_task["error_message"] == (
            "Execution was intentionally failed by task title"
        )
        assert failed_task["completed_at"] is not None


@pytest.mark.asyncio
async def test_completed_task_cannot_be_cancelled() -> None:
    async with httpx.AsyncClient(base_url=API_URL, timeout=5) as client:
        response = await client.post(
            "/api/v1/tasks",
            json={
                "title": f"completed-integration-{uuid4()}",
                "description": "Verifies cancellation is rejected for a final task state.",
                "priority": "MEDIUM",
            },
        )
        assert response.status_code == 202
        task_id = response.json()["id"]

        await wait_for_status(client, task_id, "COMPLETED")

        cancel_response = await client.delete(f"/api/v1/tasks/{task_id}")
        assert cancel_response.status_code == 409
        assert "cannot be cancelled" in cancel_response.json()["detail"]
