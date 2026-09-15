from __future__ import annotations

from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_persistence.base import Base, TimestampMixin


class KnowledgeBase(TimestampMixin, Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "name"))
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Document(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        ForeignKeyConstraint(["tenant_id", "knowledge_base_id"], ["knowledge_bases.tenant_id", "knowledge_bases.id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    active_version_id: Mapped[str | None] = mapped_column(String(36))
    acl_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class DocumentAclRow(Base):
    __tablename__ = "document_acl"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(24), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(36), primary_key=True, default="")


class DocumentVersion(TimestampMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("tenant_id", "id"),)
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(240), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(80), nullable=False)
    chunker_version: Mapped[str] = mapped_column(String(80), nullable=False)
    index_version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="draft")


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (UniqueConstraint("tenant_id", "id"),)
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    page: Mapped[int | None] = mapped_column(Integer)
    heading_path: Mapped[str | None] = mapped_column(String(500))


class ImportJob(TimestampMixin, Base):
    __tablename__ = "import_jobs"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    graph_run_id: Mapped[str | None] = mapped_column(String(36))
    stage: Mapped[str] = mapped_column(String(40), nullable=False, default="queued")
    completed_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_units: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))

