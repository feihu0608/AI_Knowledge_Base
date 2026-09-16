from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_application.ingestion_service import IngestionApplicationService, IngestionRequestError
from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Document, DocumentAclRow, DocumentVersion, ImportJob, KnowledgeBase

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


@router.get("/{knowledge_base_id}/documents")
def list_documents(
    knowledge_base_id: str,
    context: AccessContext = Depends(require_permission("knowledge.read")),
    session: Session = Depends(get_session),
) -> list[dict]:
    if session.get(KnowledgeBase, (context.tenant_id, knowledge_base_id)) is None:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    rows = session.scalars(select(Document).where(Document.tenant_id == context.tenant_id, Document.knowledge_base_id == knowledge_base_id).order_by(Document.updated_at.desc())).all()
    result = []
    for row in rows:
        acl = session.scalars(select(DocumentAclRow).where(DocumentAclRow.tenant_id == context.tenant_id, DocumentAclRow.document_id == row.id)).all()
        version = session.scalar(select(DocumentVersion).where(
            DocumentVersion.tenant_id == context.tenant_id,
            DocumentVersion.document_id == row.id,
        ).order_by(DocumentVersion.created_at.desc()).limit(1))
        job = session.scalar(select(ImportJob).where(
            ImportJob.tenant_id == context.tenant_id,
            ImportJob.document_id == row.id,
        ).order_by(ImportJob.created_at.desc()).limit(1))
        result.append({
            "id": row.id, "title": row.title, "enabled": row.enabled,
            "retrievable": bool(row.enabled and row.active_version_id),
            "active_version_id": row.active_version_id,
            "version_status": version.status if version else None,
            "import_stage": job.stage if job else None,
            "error_code": job.error_code if job else None,
            "source_filename": version.source_filename if version else None,
            "updated_at": row.updated_at.isoformat(),
            "acl_version": row.acl_version,
            "acl": [{"subject_type": x.subject_type, "subject_id": x.subject_id} for x in acl],
        })
    return result


class DocumentAclRequest(BaseModel):
    global_public: bool = False
    departments: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    users: list[str] = Field(default_factory=list)


@router.put("/{knowledge_base_id}/documents/{document_id}/acl")
def update_document_acl(
    knowledge_base_id: str,
    document_id: str,
    payload: DocumentAclRequest,
    context: AccessContext = Depends(require_permission("knowledge.admin")),
    session: Session = Depends(get_session),
) -> dict:
    row = session.get(Document, (context.tenant_id, document_id))
    if row is None or row.knowledge_base_id != knowledge_base_id:
        raise HTTPException(status_code=404, detail="document not found")
    existing = session.scalars(select(DocumentAclRow).where(DocumentAclRow.tenant_id == context.tenant_id, DocumentAclRow.document_id == document_id)).all()
    for item in existing: session.delete(item)
    subjects = ([('global', '*')] if payload.global_public else []) + [('department', x) for x in payload.departments] + [('role', x) for x in payload.roles] + [('user', x) for x in payload.users]
    for subject_type, subject_id in subjects: session.add(DocumentAclRow(tenant_id=context.tenant_id, document_id=document_id, subject_type=subject_type, subject_id=subject_id))
    row.acl_version += 1
    session.commit()
    return {"document_id": row.id, "acl_version": row.acl_version, "acl": [{"subject_type": x, "subject_id": y} for x, y in subjects]}


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


@router.get("/imports")
def list_import_jobs(
    knowledge_base_id: str = Query(...),
    context: AccessContext = Depends(require_permission("knowledge.read")),
    session: Session = Depends(get_session),
) -> list[dict]:
    if session.get(KnowledgeBase, (context.tenant_id, knowledge_base_id)) is None:
        raise HTTPException(status_code=404, detail="knowledge base not found")
    rows = session.execute(
        select(ImportJob, Document).join(
            Document,
            (Document.tenant_id == ImportJob.tenant_id) & (Document.id == ImportJob.document_id),
        ).where(
            ImportJob.tenant_id == context.tenant_id,
            Document.knowledge_base_id == knowledge_base_id,
        ).order_by(ImportJob.created_at.desc()).limit(50)
    ).all()
    return [{
        "id": job.id, "document_id": job.document_id, "version_id": job.version_id,
        "title": document.title, "stage": job.stage, "completed_units": job.completed_units,
        "total_units": job.total_units, "error_code": job.error_code,
        "updated_at": job.updated_at.isoformat(),
    } for job, document in rows]
