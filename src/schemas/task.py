from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.common.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    priority: TaskPriority = TaskPriority.MEDIUM


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: dict[str, Any] | None
    error_message: str | None


class TaskCreatedResponse(BaseModel):
    id: UUID
    status: TaskStatus
    created_at: datetime


class TaskStatusResponse(BaseModel):
    id: UUID
    status: TaskStatus
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None


class TaskListResponse(BaseModel):
    items: list[TaskResponse]
    page: int
    page_size: int
    total: int
