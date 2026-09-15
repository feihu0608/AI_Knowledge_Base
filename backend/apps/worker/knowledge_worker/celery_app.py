from __future__ import annotations

import os

from celery import Celery


celery_app = Celery(
    "knowledge_worker",
    broker=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
    include=["knowledge_worker.tasks.outbox", "knowledge_worker.tasks.ingestion"],
)
celery_app.conf.update(
    task_serializer="json", accept_content=["json"], result_serializer="json",
    timezone="Asia/Shanghai", enable_utc=True, task_acks_late=True,
    worker_prefetch_multiplier=1, task_reject_on_worker_lost=True,
    beat_schedule={"dispatch-outbox": {"task": "outbox.dispatch", "schedule": 5.0}},
)
