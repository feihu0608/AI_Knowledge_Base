from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from knowledge_application.chat_service import ChatApplicationService, ChatRequestError
from knowledge_domain.authorization.models import AccessContext

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
