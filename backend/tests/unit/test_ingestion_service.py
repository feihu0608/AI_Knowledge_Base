from pathlib import Path

import pytest
from sqlalchemy import select

from knowledge_application.ingestion_service import IngestionApplicationService, IngestionRequestError
from knowledge_application.storage import LocalObjectStorage
from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence import Base, Database, OutboxRepository
from knowledge_persistence.models import Document, DocumentAclRow, ImportJob, KnowledgeBase, OutboxEvent


def _context(tenant_id: str = "tenant-a") -> AccessContext:
    return AccessContext(
        tenant_id=tenant_id, user_id="manager-a", department_id="dept-a",
        feature_permissions=frozenset({"knowledge.write"}),
    )


def test_queue_import_persists_source_acl_job_and_outbox(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'ingestion.db'}")
    Base.metadata.create_all(database.engine)
    storage = LocalObjectStorage(tmp_path / "objects")
    service = IngestionApplicationService(storage, OutboxRepository(), provider_mode="mock")
    with database.session_factory() as session:
        session.add(KnowledgeBase(tenant_id="tenant-a", id="kb-a", name="制度库"))
        session.commit()
        result = service.queue(
            session, _context(), knowledge_base_id="kb-a", filename="../员工 制度.md",
            content="# 员工制度\n\n这是虚构演示数据。".encode(),
        )
    with database.session_factory() as session:
        document = session.get(Document, ("tenant-a", result.document_id))
        job = session.get(ImportJob, ("tenant-a", result.job_id))
        acl = session.scalar(select(DocumentAclRow).where(DocumentAclRow.document_id == result.document_id))
        event = session.scalar(select(OutboxEvent).where(OutboxEvent.aggregate_id == result.document_id))
        assert document is not None and document.active_version_id is None
        assert job is not None and job.stage == "queued"
        assert acl is not None and (acl.subject_type, acl.subject_id) == ("user", "manager-a")
        assert event is not None and event.status == "pending"
    sources = list((tmp_path / "objects" / "tenant-a").rglob("*.md"))
    assert len(sources) == 1 and sources[0].name == "员工_制度.md"


def test_cross_tenant_knowledge_base_is_hidden(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'isolation.db'}")
    Base.metadata.create_all(database.engine)
    storage = LocalObjectStorage(tmp_path / "objects")
    service = IngestionApplicationService(storage, OutboxRepository())
    with database.session_factory() as session:
        session.add(KnowledgeBase(tenant_id="tenant-b", id="kb-b", name="B库"))
        session.commit()
        with pytest.raises(IngestionRequestError, match="not found"):
            service.queue(
                session, _context("tenant-a"), knowledge_base_id="kb-b",
                filename="policy.pdf", content=b"fictional pdf payload",
            )
    assert not list((tmp_path / "objects").rglob("*.*"))
