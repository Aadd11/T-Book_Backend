from celery import Celery
from .config import settings

celery_app = Celery(
    "book_search_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.scrape"],
)

celery_app.conf.update(
    task_serializer="pickle",
    accept_content=["pickle", "json"],
    result_serializer="pickle",
    event_serializer="json",
    timezone="UTC",
    enable_utc=True,
    broker_connection_max_retries=10,
    task_default_retry_delay=120,
    result_extended=True,
    task_track_started=True,
    worker_proc_alive_timeout=300,
    broker_connection_retry_on_startup=True,
)