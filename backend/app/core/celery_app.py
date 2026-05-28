from celery import Celery

from app.core.config import get_settings


settings = get_settings()
celery_app = Celery("sentinelsafe", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_routes={"app.tasks.worker.*": {"queue": "safety"}},
    timezone="UTC",
    task_track_started=True,
)
