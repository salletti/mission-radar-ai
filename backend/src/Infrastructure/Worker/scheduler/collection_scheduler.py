import logging

from celery.beat import Scheduler

logger = logging.getLogger(__name__)

_DISPATCH_ENTRY = "dispatch-collection"


class DynamicCollectionScheduler(Scheduler):
    """
    Scheduler Beat custom qui exécute dispatch_collection() directement dans le processus Beat.

    Celery Beat appelle normalement apply_entry() → send_task() → RabbitMQ.
    Ici on court-circuite ce chemin pour l'entrée "dispatch-collection" :
    la fonction est exécutée localement, sans passer par le broker.

    Seuls les messages collect_posts.delay() (travail coûteux) transitent par RabbitMQ.
    """

    def apply_entry(self, entry, producer=None):
        if entry.name == _DISPATCH_ENTRY:
            from src.Infrastructure.Worker.scheduler.dispatch_collection import dispatch_collection

            try:
                dispatch_collection()
            except Exception:
                logger.exception("dispatch_collection() failed — Beat continues")
            return  # pas de send_task, pas de message broker
        return super().apply_entry(entry, producer=producer)
