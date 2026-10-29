"""PlacementOS Celery Application Configuration."""

from celery import Celery  # type: ignore[import-untyped]

from placementos.core.config import settings

celery_app = Celery(
    "placementos",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "placementos.workers.source_tasks",
        "placementos.workers.eligibility_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="placementos.workers.ping")
def ping_task() -> str:
    """Diagnostic task for verifying Celery worker health."""
    return "pong"
