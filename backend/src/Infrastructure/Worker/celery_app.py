from celery import Celery
from celery.schedules import crontab

from src.Infrastructure.Config.settings import settings

celery_app = Celery(
    "mission_radar",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "src.Infrastructure.Worker.tasks.ping_task",
        "src.Infrastructure.Worker.tasks.collect_posts_task",
        "src.Infrastructure.Worker.tasks.analyze_post_task",
        "src.Infrastructure.Worker.tasks.run_mission_refresh_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="default",
)

# DynamicCollectionScheduler exécute dispatch_collection() directement dans Beat —
# sans message RabbitMQ intermédiaire. Seuls les collect_posts.delay() transitent par le broker.
celery_app.conf.beat_scheduler = (
    "src.Infrastructure.Worker.scheduler.collection_scheduler:DynamicCollectionScheduler"
)

# Dev : toutes les 5 minutes (itération rapide) | Prod : une fois par jour à 7h00 UTC
_DISPATCH_SCHEDULE = crontab(hour=7, minute=0) if settings.APP_ENV == "production" else 300.0

celery_app.conf.beat_schedule = {
    "dispatch-collection": {
        "task": "dispatch-collection",  # marqueur intercepté par DynamicCollectionScheduler
        "schedule": _DISPATCH_SCHEDULE,
    }
}
