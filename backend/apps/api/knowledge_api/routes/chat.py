from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_application.chat_service import ChatApplicationService, ChatRequestError
from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Conversation, Message

from knowledge_api.dependencies import get_chat_service, get_session, require_permission


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


@router.post("")
def chat(
    payload: ChatRequest,
    context: AccessContext = Depends(require_permission("chat.use")),
    session: Session = Depends(get_session),
    service: ChatApplicationService = Depends(get_chat_service),
) -> dict:
    try:
        result = service.ask(
            session, context, question=payload.question, conversation_id=payload.conversation_id
        )
    except ChatRequestError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc) else 400, detail=str(exc)) from exc
    return {
        "conversation_id": result.conversation_id, "message_id": result.message_id,
        "answer": result.answer, "evidence": result.evidence, "warnings": result.warnings,
        "provider_mode": result.provider_mode,
    }


@router.get("/conversations")
def list_conversations(
    context: AccessContext = Depends(require_permission("chat.use")),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.scalars(
        select(Conversation).where(
            Conversation.tenant_id == context.tenant_id,
            Conversation.owner_id == context.user_id,
        ).order_by(Conversation.updated_at.desc())
    ).all()
    return [{"id": row.id, "title": row.title, "created_at": row.created_at.isoformat(), "updated_at": row.updated_at.isoformat()} for row in rows]


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    context: AccessContext = Depends(require_permission("chat.use")),
    session: Session = Depends(get_session),
) -> dict:
    conversation = session.get(Conversation, (context.tenant_id, conversation_id))
    if conversation is None or conversation.owner_id != context.user_id:
        raise HTTPException(status_code=404, detail="conversation not found")
    messages = session.scalars(
        select(Message).where(
            Message.tenant_id == context.tenant_id,
            Message.conversation_id == conversation_id,
        ).order_by(Message.created_at.asc())
    ).all()
    return {"id": conversation.id, "title": conversation.title, "messages": [{"id": m.id, "role": m.role, "status": m.status, "content": m.content, "created_at": m.created_at.isoformat()} for m in messages]}
