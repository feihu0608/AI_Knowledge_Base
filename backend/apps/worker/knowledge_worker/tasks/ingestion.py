from __future__ import annotations

from hashlib import sha256
import json

from knowledge_persistence.models import Chunk, Document, DocumentVersion, ImportJob, OutboxEvent

from knowledge_worker.celery_app import celery_app
from knowledge_worker.runtime import build_ingestion_graph, database, storage


@celery_app.task(name="ingestion.process", autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def process_ingestion(event_id: str) -> dict:
    with database.session_factory() as session:
        event = session.get(OutboxEvent, event_id)
        if event is None or event.event_type != "document.import.requested":
            return {"status": "ignored"}
        payload = json.loads(event.payload_json)
        job = session.get(ImportJob, (event.tenant_id, payload["job_id"]))
        version = session.get(DocumentVersion, (event.tenant_id, payload["version_id"]))
        document = session.get(Document, (event.tenant_id, event.aggregate_id))
        if job is None or version is None or document is None:
            raise RuntimeError("import aggregate is incomplete")
        if job.stage == "published":
            return {"status": "already_processed", "job_id": job.id}
        job.stage = "validating"
        job.completed_units = 0
        session.commit()

    try:
        content = storage.read(payload["object_key"])
        def persist_progress(stage: str, completed: int, total: int) -> None:
            with database.session_factory() as progress_session:
                progress_job = progress_session.get(ImportJob, (event.tenant_id, payload["job_id"]))
                if progress_job is not None:
                    progress_job.stage = stage
                    progress_job.completed_units = completed
                    progress_job.total_units = total
                    progress_session.commit()

        result = build_ingestion_graph(progress_callback=persist_progress).invoke({
            "tenant_id": event.tenant_id, "actor_id": "system-worker",
            "knowledge_base_id": document.knowledge_base_id, "document_id": document.id,
            "version_id": version.id, "filename": version.source_filename, "content": content,
            "provider_mode": payload["provider_mode"], "stage": "queued", "index_version": version.index_version,
        })
        if result.get("status") != "succeeded":
            raise RuntimeError(result.get("error_code", "ingestion_graph_failed"))
        with database.session_factory() as session:
            job = session.get(ImportJob, (event.tenant_id, payload["job_id"]))
            version = session.get(DocumentVersion, (event.tenant_id, payload["version_id"]))
            document = session.get(Document, (event.tenant_id, event.aggregate_id))
            for item in result.get("chunks", []):
                chunk_id = sha256(f'{event.tenant_id}:{version.id}:{item["ordinal"]}'.encode()).hexdigest()[:32]
                session.merge(Chunk(
                    tenant_id=event.tenant_id, id=chunk_id, document_id=document.id,
                    version_id=version.id, ordinal=item["ordinal"], text=item["text"],
                ))
            version.status = "published"
            document.active_version_id = version.id
            job.stage = "published"
            job.completed_units = job.total_units
            session.commit()
        return {"status": "published", "job_id": payload["job_id"], "chunks": len(result.get("chunks", []))}
    except Exception as exc:
        with database.session_factory() as session:
            job = session.get(ImportJob, (event.tenant_id, payload["job_id"]))
            version = session.get(DocumentVersion, (event.tenant_id, payload["version_id"]))
            if job is not None:
                job.stage, job.error_code = "failed", type(exc).__name__
            if version is not None:
                version.status = "failed"
            session.commit()
        raise
