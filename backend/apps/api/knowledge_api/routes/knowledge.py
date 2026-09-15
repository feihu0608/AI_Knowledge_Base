from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_application.ingestion_service import IngestionApplicationService, IngestionRequestError
from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import ImportJob, KnowledgeBase

from knowledge_api.dependencies import get_ingestion_service, get_session, require_permission


router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])


class CreateKnowledgeBaseRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)


@router.get("")
def list_knowledge_bases(
    context: AccessContext = Depends(require_permission("knowledge.read")),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.scalars(select(KnowledgeBase).where(
        KnowledgeBase.tenant_id == context.tenant_id
    ).order_by(KnowledgeBase.name)).all()
    return [{"id": row.id, "name": row.name, "enabled": row.enabled} for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_knowledge_base(
    payload: CreateKnowledgeBaseRequest,
    context: AccessContext = Depends(require_permission("knowledge.admin")),
    session: Session = Depends(get_session),
) -> dict:
    row = KnowledgeBase(tenant_id=context.tenant_id, id=str(uuid4()), name=payload.name, enabled=True)
    session.add(row)
    session.commit()
    return {"id": row.id, "name": row.name, "enabled": row.enabled}


@router.post("/{knowledge_base_id}/documents", status_code=status.HTTP_202_ACCEPTED)
def upload_document(
    knowledge_base_id: str,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    context: AccessContext = Depends(require_permission("knowledge.write")),
    session: Session = Depends(get_session),
    service: IngestionApplicationService = Depends(get_ingestion_service),
) -> dict:
    try:
        result = service.queue(
            session, context, knowledge_base_id=knowledge_base_id,
            filename=file.filename or "document.bin", content=file.file.read(), title=title,
        )
    except IngestionRequestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "document_id": result.document_id, "version_id": result.version_id, "job_id": result.job_id,
        "stage": result.stage, "provider_mode": result.provider_mode,
    }


@router.get("/imports/{job_id}")
def get_import_job(
    job_id: str,
    context: AccessContext = Depends(require_permission("knowledge.read")),
    session: Session = Depends(get_session),
) -> dict:
    job = session.get(ImportJob, (context.tenant_id, job_id))
    if job is None:
        raise HTTPException(status_code=404, detail="import job not found")
    return {"id": job.id, "document_id": job.document_id, "version_id": job.version_id,
            "stage": job.stage, "completed_units": job.completed_units,
            "total_units": job.total_units, "error_code": job.error_code}
