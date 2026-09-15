from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Document, DocumentAclRow, DocumentVersion, ImportJob, KnowledgeBase
from knowledge_persistence.repositories import OutboxRepository

from .storage import LocalObjectStorage


class IngestionRequestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class QueuedImport:
    document_id: str
    version_id: str
    job_id: str
    stage: str
    provider_mode: str


class IngestionApplicationService:
    allowed_extensions = {".pdf", ".md", ".txt", ".doc", ".docx"}

    def __init__(self, storage: LocalObjectStorage, outbox: OutboxRepository,
                 *, max_upload_bytes: int = 50 * 1024 * 1024, provider_mode: str = "mock") -> None:
        self.storage = storage
        self.outbox = outbox
        self.max_upload_bytes = max_upload_bytes
        self.provider_mode = provider_mode

    def queue(self, session: Session, context: AccessContext, *, knowledge_base_id: str,
              filename: str, content: bytes, title: str | None = None) -> QueuedImport:
        if not content:
            raise IngestionRequestError("empty document")
        if len(content) > self.max_upload_bytes:
            raise IngestionRequestError("document exceeds upload limit")
        if Path(filename).suffix.lower() not in self.allowed_extensions:
            raise IngestionRequestError("unsupported document format")
        knowledge_base = session.get(KnowledgeBase, (context.tenant_id, knowledge_base_id))
        if knowledge_base is None or not knowledge_base.enabled:
            raise IngestionRequestError("knowledge base not found")

        document_id, version_id, job_id = str(uuid4()), str(uuid4()), str(uuid4())
        object_key = self.storage.put_source(
            tenant_id=context.tenant_id, document_id=document_id, version_id=version_id,
            filename=filename, content=content,
        )
        try:
            session.add_all([
                Document(
                    tenant_id=context.tenant_id, id=document_id, knowledge_base_id=knowledge_base_id,
                    title=(title or Path(filename).stem)[:240], enabled=True, acl_version=1,
                ),
                DocumentAclRow(
                    tenant_id=context.tenant_id, document_id=document_id,
                    subject_type="user", subject_id=context.user_id,
                ),
                DocumentVersion(
                    tenant_id=context.tenant_id, id=version_id, document_id=document_id,
                    source_filename=self.storage.safe_filename(filename), source_sha256=sha256(content).hexdigest(),
                    parser_version="mineru-api-v1", chunker_version="heading-aware-v1",
                    index_version="bge-large-zh-v1.5-v1", status="queued",
                ),
                ImportJob(
                    tenant_id=context.tenant_id, id=job_id, document_id=document_id,
                    version_id=version_id, stage="queued", completed_units=0, total_units=7,
                ),
            ])
            self.outbox.add(
                session, tenant_id=context.tenant_id, event_type="document.import.requested",
                aggregate_id=document_id, aggregate_version=1,
                payload={"job_id": job_id, "version_id": version_id, "object_key": object_key,
                         "provider_mode": self.provider_mode},
            )
            session.commit()
        except Exception:
            session.rollback()
            self.storage.delete(object_key)
            raise
        return QueuedImport(document_id, version_id, job_id, "queued", self.provider_mode)
