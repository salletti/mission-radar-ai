from celery.result import AsyncResult
from fastapi import APIRouter
from pydantic import BaseModel

from src.Infrastructure.Worker.celery_app import celery_app
from src.Infrastructure.Worker.tasks.ping_task import ping

router = APIRouter(prefix="/api/tasks")


class PingRequest(BaseModel):
    message: str


@router.post("/ping")
def send_ping(body: PingRequest) -> dict:
    task = ping.delay(body.message)
    return {"task_id": task.id}


@router.get("/{task_id}")
def get_task_result(task_id: str) -> dict:
    result = AsyncResult(task_id, app=celery_app)
    if result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    if result.state == "FAILURE":
        return {"task_id": task_id, "status": "failure", "error": str(result.result)}
    return {"task_id": task_id, "status": result.state.lower(), "result": result.result}
