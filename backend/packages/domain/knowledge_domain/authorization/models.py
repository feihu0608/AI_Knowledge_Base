from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AccessContext:
    tenant_id: str
    user_id: str
    department_id: str
    ancestor_department_ids: frozenset[str] = field(default_factory=frozenset)
    role_ids: frozenset[str] = field(default_factory=frozenset)
    feature_permissions: frozenset[str] = field(default_factory=frozenset)
    authz_version: int = 1
    active: bool = True

    @property
    def department_scope_ids(self) -> frozenset[str]:
        return self.ancestor_department_ids | frozenset({self.department_id})


@dataclass(frozen=True, slots=True)
class DocumentAcl:
    global_visible: bool = False
    department_ids: frozenset[str] = field(default_factory=frozenset)
    role_ids: frozenset[str] = field(default_factory=frozenset)
    user_ids: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_empty(self) -> bool:
        return not (self.global_visible or self.department_ids or self.role_ids or self.user_ids)


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    tenant_id: str
    document_id: str
    enabled: bool
    active_version_id: str | None
    acl_version: int
    acl: DocumentAcl

