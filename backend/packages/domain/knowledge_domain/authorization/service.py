from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from .models import AccessContext, DocumentRecord


class DenialReason(StrEnum):
    INACTIVE_USER = "inactive_user"
    CROSS_TENANT = "cross_tenant"
    FEATURE_DENIED = "feature_denied"
    DOCUMENT_DISABLED = "document_disabled"
    NO_ACTIVE_VERSION = "no_active_version"
    EMPTY_ACL = "empty_acl"
    ACL_DENIED = "acl_denied"


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str
    matched_dimension: str | None = None


class AuthorizationService:
    """Deterministic RBAC + four-dimensional document ACL evaluator."""

    def can_read(
        self,
        context: AccessContext,
        document: DocumentRecord,
        *,
        required_feature: str | None = None,
    ) -> AuthorizationDecision:
        if not context.active:
            return AuthorizationDecision(False, DenialReason.INACTIVE_USER)
        if context.tenant_id != document.tenant_id:
            return AuthorizationDecision(False, DenialReason.CROSS_TENANT)
        if required_feature and required_feature not in context.feature_permissions:
            return AuthorizationDecision(False, DenialReason.FEATURE_DENIED)
        if not document.enabled:
            return AuthorizationDecision(False, DenialReason.DOCUMENT_DISABLED)
        if not document.active_version_id:
            return AuthorizationDecision(False, DenialReason.NO_ACTIVE_VERSION)
        if document.acl.is_empty:
            return AuthorizationDecision(False, DenialReason.EMPTY_ACL)
        if document.acl.global_visible:
            return AuthorizationDecision(True, "allowed", "global")
        if document.acl.department_ids & context.department_scope_ids:
            return AuthorizationDecision(True, "allowed", "department")
        if document.acl.role_ids & context.role_ids:
            return AuthorizationDecision(True, "allowed", "role")
        if context.user_id in document.acl.user_ids:
            return AuthorizationDecision(True, "allowed", "user")
        return AuthorizationDecision(False, DenialReason.ACL_DENIED)

    def filter_documents(
        self,
        context: AccessContext,
        documents: Iterable[DocumentRecord],
    ) -> tuple[list[DocumentRecord], list[str]]:
        allowed: list[DocumentRecord] = []
        restricted_ids: list[str] = []
        for document in documents:
            decision = self.can_read(context, document)
            if decision.allowed:
                allowed.append(document)
            else:
                restricted_ids.append(document.document_id)
        return allowed, restricted_ids

