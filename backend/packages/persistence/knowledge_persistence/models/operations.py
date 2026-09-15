from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_persistence.base import Base, TimestampMixin


class FaqCandidate(TimestampMixin, Base):
    __tablename__ = "faq_candidates"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")
    representative_question: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_answer: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    unique_users: Mapped[int] = mapped_column(Integer, nullable=False)


class FaqItem(TimestampMixin, Base):
    __tablename__ = "faq_items"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    acl_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class KnowledgeGap(TimestampMixin, Base):
    __tablename__ = "knowledge_gaps"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    representative_question: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")


class OutboxEvent(TimestampMixin, Base):
    __tablename__ = "outbox_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")

