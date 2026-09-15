from __future__ import annotations

from dataclasses import dataclass
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_persistence.models import DepartmentClosure, OutboxEvent, RolePermission, User, UserRole


@dataclass(frozen=True, slots=True)
class UserIdentityRow:
    user: User
    role_ids: tuple[str, ...]
    permissions: tuple[str, ...]
    ancestor_department_ids: tuple[str, ...]


class UserRepository:
    def find_identity(self, session: Session, *, tenant_id: str, username: str) -> UserIdentityRow | None:
        user = session.scalar(select(User).where(User.tenant_id == tenant_id, User.username == username))
        return None if user is None else self._load(session, user)

    def get_identity(self, session: Session, *, tenant_id: str, user_id: str) -> UserIdentityRow | None:
        user = session.scalar(select(User).where(User.tenant_id == tenant_id, User.id == user_id))
        return None if user is None else self._load(session, user)

    def _load(self, session: Session, user: User) -> UserIdentityRow:
        role_ids = tuple(session.scalars(select(UserRole.role_id).where(
            UserRole.tenant_id == user.tenant_id, UserRole.user_id == user.id
        )).all())
        permissions = tuple(session.scalars(select(RolePermission.permission_code).where(
            RolePermission.tenant_id == user.tenant_id, RolePermission.role_id.in_(role_ids)
        )).all()) if role_ids else ()
        ancestors = tuple(session.scalars(select(DepartmentClosure.ancestor_id).where(
            DepartmentClosure.tenant_id == user.tenant_id,
            DepartmentClosure.descendant_id == user.department_id,
        )).all())
        return UserIdentityRow(user, role_ids, permissions, ancestors)


class OutboxRepository:
    def add(self, session: Session, *, tenant_id: str, event_type: str, aggregate_id: str,
            aggregate_version: int, payload: dict) -> OutboxEvent:
        event = OutboxEvent(
            id=str(uuid4()), tenant_id=tenant_id, event_type=event_type,
            aggregate_id=aggregate_id, aggregate_version=aggregate_version,
            payload_json=json.dumps(payload, ensure_ascii=False, separators=(",", ":")), status="pending",
        )
        session.add(event)
        return event
