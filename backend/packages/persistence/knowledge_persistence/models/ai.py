from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_persistence.base import Base, TimestampMixin


class GraphRun(TimestampMixin, Base):
    __tablename__ = "graph_runs"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    graph_name: Mapped[str] = mapped_column(String(100), nullable=False)
    graph_version: Mapped[str] = mapped_column(String(40), nullable=False)
    business_key: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(16), nullable=False)


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class AnswerEvidence(Base):
    __tablename__ = "answer_evidence"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(64))
    source_version: Mapped[str | None] = mapped_column(String(80))
    acl_version: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(240), nullable=False)


class ModelCall(TimestampMixin, Base):
    __tablename__ = "model_calls"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    error_category: Mapped[str | None] = mapped_column(String(80))

