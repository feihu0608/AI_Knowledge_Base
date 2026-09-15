from pathlib import Path

import pytest
from sqlalchemy import func, select

from knowledge_application.chat_service import ChatApplicationService, ChatRequestError
from knowledge_domain.authorization.models import AccessContext
from knowledge_graphs.knowledge_answer import build_knowledge_answer_graph
from knowledge_graphs.knowledge_answer.mock_runtime import build_mock_answer_runtime
from knowledge_persistence import Base, Database
from knowledge_persistence.models import AnswerEvidence, Conversation, Message, ModelCall


def context(tenant: str, user: str) -> AccessContext:
    return AccessContext(tenant_id=tenant, user_id=user, department_id="dept", active=True)


def test_chat_result_and_evidence_are_persisted_and_labelled_mock(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'chat.db'}")
    Base.metadata.create_all(database.engine)
    service = ChatApplicationService(
        build_knowledge_answer_graph(build_mock_answer_runtime()), provider_mode="mock"
    )
    with database.session_factory() as session:
        result = service.ask(session, context("tenant-a", "alice"), question="报销规则是什么？")
    assert result.provider_mode == "mock"
    assert result.answer.startswith("[MOCK]")
    with database.session_factory() as session:
        assert session.get(Conversation, ("tenant-a", result.conversation_id)) is not None
        assert session.get(Message, ("tenant-a", result.message_id)).status == "succeeded"
        assert session.scalar(select(func.count()).select_from(AnswerEvidence)) == 1
        assert session.scalar(select(func.count()).select_from(ModelCall)) == 2


def test_user_cannot_append_to_another_users_conversation(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'chat-isolation.db'}")
    Base.metadata.create_all(database.engine)
    service = ChatApplicationService(
        build_knowledge_answer_graph(build_mock_answer_runtime()), provider_mode="mock"
    )
    with database.session_factory() as session:
        first = service.ask(session, context("tenant-a", "alice"), question="问题一")
    with database.session_factory() as session, pytest.raises(ChatRequestError, match="not found"):
        service.ask(
            session, context("tenant-a", "bob"), question="尝试越权",
            conversation_id=first.conversation_id,
        )
