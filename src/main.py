from fastapi import FastAPI

from src.api.v1.tasks import router as tasks_router


app = FastAPI(title="Async Task Service")
app.include_router(tasks_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
