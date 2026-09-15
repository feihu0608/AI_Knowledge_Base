from knowledge_domain.authorization import AccessContext, AuthorizationService, DocumentAcl, DocumentRecord


def context(**overrides):
    values = {
        "tenant_id": "tenant-a",
        "user_id": "user-1",
        "department_id": "dept-child",
        "ancestor_department_ids": frozenset({"dept-parent"}),
        "role_ids": frozenset({"role-user"}),
    }
    values.update(overrides)
    return AccessContext(**values)


def document(acl: DocumentAcl, **overrides):
    values = {
        "tenant_id": "tenant-a",
        "document_id": "doc-1",
        "enabled": True,
        "active_version_id": "v1",
        "acl_version": 1,
        "acl": acl,
    }
    values.update(overrides)
    return DocumentRecord(**values)


def test_empty_acl_denies_by_default():
    decision = AuthorizationService().can_read(context(), document(DocumentAcl()))
    assert decision.allowed is False
    assert decision.reason == "empty_acl"


def test_global_allows_same_tenant_only():
    service = AuthorizationService()
    record = document(DocumentAcl(global_visible=True))
    assert service.can_read(context(), record).matched_dimension == "global"
    assert service.can_read(context(tenant_id="tenant-b"), record).reason == "cross_tenant"


def test_parent_department_acl_covers_descendant_user():
    decision = AuthorizationService().can_read(
        context(), document(DocumentAcl(department_ids=frozenset({"dept-parent"})))
    )
    assert decision.allowed is True
    assert decision.matched_dimension == "department"


def test_role_or_personal_dimension_allows_access():
    service = AuthorizationService()
    assert service.can_read(
        context(), document(DocumentAcl(role_ids=frozenset({"role-user"})))
    ).matched_dimension == "role"
    assert service.can_read(
        context(), document(DocumentAcl(user_ids=frozenset({"user-1"})))
    ).matched_dimension == "user"


def test_sibling_department_does_not_match():
    decision = AuthorizationService().can_read(
        context(), document(DocumentAcl(department_ids=frozenset({"dept-sibling"})))
    )
    assert decision.allowed is False
    assert decision.reason == "acl_denied"

