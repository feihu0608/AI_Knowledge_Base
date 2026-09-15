from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import AnswerEvidence, Conversation, Message, ModelCall


class ChatRequestError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ChatResult:
    conversation_id: str
    message_id: str
    answer: str
    evidence: list[dict]
    warnings: list[str]
    provider_mode: str


class ChatApplicationService:
    def __init__(self, answer_graph, *, provider_mode: str) -> None:
        self.answer_graph = answer_graph
        self.provider_mode = provider_mode

    def ask(self, session: Session, context: AccessContext, *, question: str,
            conversation_id: str | None = None) -> ChatResult:
        question = question.strip()
        if not question:
            raise ChatRequestError("question is required")
        request_id = str(uuid4())
        if conversation_id:
            conversation = session.get(Conversation, (context.tenant_id, conversation_id))
            if conversation is None or conversation.owner_id != context.user_id:
                raise ChatRequestError("conversation not found")
        else:
            conversation_id = str(uuid4())
            conversation = Conversation(
                tenant_id=context.tenant_id, id=conversation_id, owner_id=context.user_id,
                title=question[:80],
            )
            session.add(conversation)
        user_message = Message(
            tenant_id=context.tenant_id, id=str(uuid4()), conversation_id=conversation_id,
            request_id=request_id, role="user", status="succeeded", content=question,
        )
        session.add(user_message)
        try:
            result = self.answer_graph.invoke({
                "tenant_id": context.tenant_id, "user_id": context.user_id, "question": question,
                "provider_mode": self.provider_mode, "status": "requested",
            })
            assistant_id = str(uuid4())
            assistant = Message(
                tenant_id=context.tenant_id, id=assistant_id, conversation_id=conversation_id,
                request_id=request_id, role="assistant", status="succeeded", content=result["answer"],
            )
            session.add(assistant)
            evidence_by_id = {item["evidence_id"]: item for item in result.get("fused_evidence", [])}
            cited = [evidence_by_id[item] for item in result.get("citation_ids", []) if item in evidence_by_id]
            for item in cited:
                session.add(AnswerEvidence(
                    tenant_id=context.tenant_id, message_id=assistant_id, evidence_id=item["evidence_id"],
                    source_type=item["source_type"], source_id=item.get("source_id"),
                    source_version=item.get("source_version"), acl_version=item.get("acl_version"), title=item["title"],
                ))
            for model_name in ("QueryPlannerAgent", "AnswerWriterAgent"):
                session.add(ModelCall(
                    tenant_id=context.tenant_id, id=str(uuid4()), request_id=request_id,
                    provider="workflow", model=model_name, provider_mode=self.provider_mode,
                    duration_ms=0, input_tokens=None, output_tokens=None,
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        return ChatResult(
            conversation_id, assistant_id, result["answer"], cited,
            result.get("warnings", []), self.provider_mode,
        )
