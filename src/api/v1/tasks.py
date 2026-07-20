from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.common.enums import TaskPriority, TaskStatus
from src.schemas.task import (
    TaskCreate,
    TaskCreatedResponse,
    TaskListResponse,
    TaskResponse,
    TaskStatusResponse,
)
from src.services.task import (
    TaskCancellationError,
    TaskNotFoundError,
    TaskService,
    get_task_service,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post(
    "", response_model=TaskCreatedResponse, status_code=status.HTTP_202_ACCEPTED
)
async def create_task(
    body: TaskCreate,
    task_service: TaskService = Depends(get_task_service),
) -> TaskCreatedResponse:
    task = await task_service.create(body)
    return TaskCreatedResponse(
        id=task.id,
        status=task.status,
        created_at=task.created_at,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority: TaskPriority | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    task_service: TaskService = Depends(get_task_service),
) -> TaskListResponse:
    tasks, total = await task_service.list(status_filter, priority, page, page_size)
    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID, task_service: TaskService = Depends(get_task_service)
) -> TaskResponse:
    try:
        return TaskResponse.model_validate(await task_service.get(task_id))
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
) -> TaskStatusResponse:
    try:
        task = await task_service.get(task_id)
        return TaskStatusResponse(
            id=task.id,
            status=task.status,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc


@router.delete("/{task_id}", response_model=TaskStatusResponse)
async def cancel_task(
    task_id: UUID,
    task_service: TaskService = Depends(get_task_service),
) -> TaskStatusResponse:
    try:
        task = await task_service.cancel(task_id)
        return TaskStatusResponse(
            id=task.id,
            status=task.status,
            started_at=task.started_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
        )
    except TaskNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Task not found") from exc
    except TaskCancellationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
