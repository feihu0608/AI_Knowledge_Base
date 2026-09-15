from __future__ import annotations

from sqlalchemy import Boolean, ForeignKeyConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from knowledge_persistence.base import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")


class Department(TimestampMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "parent_id", "name"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")


class DepartmentClosure(Base):
    __tablename__ = "department_closure"
    __table_args__ = (
        ForeignKeyConstraint(["tenant_id", "ancestor_id"], ["departments.tenant_id", "departments.id"]),
        ForeignKeyConstraint(["tenant_id", "descendant_id"], ["departments.tenant_id", "departments.id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ancestor_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    descendant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id"),
        UniqueConstraint("tenant_id", "username"),
        ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        ForeignKeyConstraint(["tenant_id", "department_id"], ["departments.tenant_id", "departments.id"]),
    )
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    department_id: Mapped[str] = mapped_column(String(36), nullable=False)
    authz_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Role(TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "id"), UniqueConstraint("tenant_id", "code"))
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class UserRole(Base):
    __tablename__ = "user_roles"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class RolePermission(Base):
    __tablename__ = "role_permissions"
    tenant_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    role_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    permission_code: Mapped[str] = mapped_column(String(120), primary_key=True)

