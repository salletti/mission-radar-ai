from src.Infrastructure.Worker.celery_app import celery_app


@celery_app.task(name="tasks.ping")
def ping(message: str) -> dict:
    return {"message": message, "worker": "ok"}
