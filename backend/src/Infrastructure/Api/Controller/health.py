from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Config.database import get_db_session
from src.Infrastructure.Messaging.rabbitmq_client import rabbitmq_client
from src.Infrastructure.Messaging.redis_client import redis_client

router = APIRouter()


@router.get("/")
def root():
    return {"name": "mission-radar-ai", "version": "0.1.0"}


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db_session)):
    try:
        await db.execute(text("SELECT 1"))
        postgres_status = "up"
    except Exception:
        postgres_status = "down"

    rabbitmq_status = "up" if await rabbitmq_client.ping() else "down"
    redis_status = "up" if await redis_client.ping() else "down"
    celery_broker_status = rabbitmq_status
    celery_backend_status = redis_status

    all_up = all(
        s == "up"
        for s in [postgres_status, rabbitmq_status, redis_status, celery_broker_status, celery_backend_status]
    )
    return {
        "status": "ok" if all_up else "degraded",
        "services": {
            "api": "up",
            "postgres": postgres_status,
            "rabbitmq": rabbitmq_status,
            "redis": redis_status,
            "celery_broker": celery_broker_status,
            "celery_backend": celery_backend_status,
        },
    }
