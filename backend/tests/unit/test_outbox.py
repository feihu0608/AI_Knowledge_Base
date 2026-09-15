import json

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from knowledge_persistence import Base, OutboxRepository
from knowledge_persistence.models import OutboxEvent


def test_outbox_event_joins_business_transaction() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        event = OutboxRepository().add(
            session, tenant_id="tenant-a", event_type="document.import.requested",
            aggregate_id="doc-1", aggregate_version=1, payload={"version_id": "v1"},
        )
        session.commit()
        event_id = event.id
    with Session(engine) as session:
        saved = session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        assert saved is not None
        assert saved.tenant_id == "tenant-a"
        assert json.loads(saved.payload_json) == {"version_id": "v1"}
