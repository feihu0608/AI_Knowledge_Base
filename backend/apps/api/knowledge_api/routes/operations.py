from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import FaqCandidate, FaqItem, KnowledgeGap

from knowledge_api.dependencies import get_session, require_permission

router = APIRouter(prefix="/api/operations", tags=["operations"])


class FaqEditRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(min_length=1, max_length=10000)


class FaqStateRequest(BaseModel):
    status: str | None = Field(default=None, pattern="^(enabled|disabled)$")
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    answer: str | None = Field(default=None, min_length=1, max_length=10000)


@router.get("/faq/candidates")
def list_candidates(context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(FaqCandidate).where(FaqCandidate.tenant_id == context.tenant_id).order_by(FaqCandidate.frequency.desc())).all()
    return [{"id": r.id, "question": r.representative_question, "answer": r.proposed_answer, "frequency": r.frequency, "unique_users": r.unique_users, "state": r.state, "updated_at": r.updated_at.isoformat()} for r in rows]


@router.patch("/faq/candidates/{candidate_id}")
def edit_candidate(candidate_id: str, payload: FaqEditRequest, context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> dict:
    row = session.get(FaqCandidate, (context.tenant_id, candidate_id))
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ candidate not found")
    row.representative_question, row.proposed_answer = payload.question, payload.answer
    session.commit()
    return {"id": row.id, "question": row.representative_question, "answer": row.proposed_answer, "state": row.state}


@router.post("/faq/candidates/{candidate_id}/publish")
def publish_candidate(candidate_id: str, payload: FaqEditRequest, context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> dict:
    row = session.get(FaqCandidate, (context.tenant_id, candidate_id))
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ candidate not found")
    row.representative_question, row.proposed_answer, row.state = payload.question, payload.answer, "approved"
    item = FaqItem(tenant_id=context.tenant_id, id=str(uuid4()), version=1, status="enabled", question=payload.question, answer=payload.answer, acl_version=1)
    session.add(item)
    session.commit()
    return {"id": item.id, "question": item.question, "answer": item.answer, "status": item.status, "version": item.version}


@router.post("/faq/candidates/{candidate_id}/reject")
def reject_candidate(candidate_id: str, context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> dict:
    row = session.get(FaqCandidate, (context.tenant_id, candidate_id))
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ candidate not found")
    row.state = "rejected"
    session.commit()
    return {"id": row.id, "state": row.state}


@router.get("/faq/published")
def list_published(context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(FaqItem).where(FaqItem.tenant_id == context.tenant_id).order_by(FaqItem.updated_at.desc())).all()
    return [{"id": r.id, "question": r.question, "answer": r.answer, "status": r.status, "version": r.version, "updated_at": r.updated_at.isoformat()} for r in rows]


@router.patch("/faq/published/{faq_id}")
def update_published(faq_id: str, payload: FaqStateRequest, context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> dict:
    row = session.get(FaqItem, (context.tenant_id, faq_id))
    if row is None:
        raise HTTPException(status_code=404, detail="FAQ not found")
    if payload.status is not None: row.status = payload.status
    if payload.question is not None: row.question = payload.question
    if payload.answer is not None: row.answer = payload.answer
    row.version += 1
    session.commit()
    return {"id": row.id, "status": row.status, "version": row.version}


@router.get("/gaps")
def list_gaps(context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(KnowledgeGap).where(KnowledgeGap.tenant_id == context.tenant_id, KnowledgeGap.status == "open").order_by(KnowledgeGap.frequency.desc())).all()
    return [{"id": r.id, "question": r.representative_question, "frequency": r.frequency, "reason": r.reason, "status": r.status, "updated_at": r.updated_at.isoformat()} for r in rows]


@router.post("/gaps/{gap_id}/task")
def create_gap_task(gap_id: str, context: AccessContext = Depends(require_permission("faq.review")), session: Session = Depends(get_session)) -> dict:
    row = session.get(KnowledgeGap, (context.tenant_id, gap_id))
    if row is None:
        raise HTTPException(status_code=404, detail="knowledge gap not found")
    row.status = "task_created"
    session.commit()
    return {"id": row.id, "status": row.status, "question": row.representative_question}
