from __future__ import annotations

from sqlalchemy import select

from knowledge_persistence.models import OutboxEvent

from knowledge_worker.celery_app import celery_app
from knowledge_worker.runtime import database


@celery_app.task(name="outbox.dispatch")
def dispatch_outbox(batch_size: int = 50) -> int:
    sent = 0
    with database.session_factory() as session:
        events = session.scalars(
            select(OutboxEvent).where(OutboxEvent.status == "pending")
            .order_by(OutboxEvent.created_at).limit(batch_size).with_for_update(skip_locked=True)
        ).all()
        for event in events:
            if event.event_type == "document.import.requested":
                celery_app.send_task("ingestion.process", args=[event.id])
                event.status = "published"
                sent += 1
        session.commit()
    return sent
