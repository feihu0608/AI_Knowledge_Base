from pathlib import Path

import pytest

from knowledge_application.auth_service import AuthenticationService, StaleAuthorizationError
from knowledge_application.security import PasswordHasher, TokenService
from knowledge_persistence import Base, Database, UserRepository
from knowledge_persistence.models import (
    Department, DepartmentClosure, Role, RolePermission, Tenant, User, UserRole,
)


def _database(tmp_path: Path) -> Database:
    database = Database(f"sqlite:///{tmp_path / 'auth.db'}")
    Base.metadata.create_all(database.engine)
    return database


def _seed(database: Database, hasher: PasswordHasher) -> None:
    with database.session_factory() as session:
        session.add_all([
            Tenant(id="tenant-a", name="虚构租户A"),
            Department(tenant_id="tenant-a", id="head", parent_id=None, name="总部"),
            Department(tenant_id="tenant-a", id="sales", parent_id="head", name="销售部"),
            DepartmentClosure(tenant_id="tenant-a", ancestor_id="head", descendant_id="sales", depth=1),
            DepartmentClosure(tenant_id="tenant-a", ancestor_id="sales", descendant_id="sales", depth=0),
            Role(tenant_id="tenant-a", id="employee", code="employee", name="员工"),
            RolePermission(tenant_id="tenant-a", role_id="employee", permission_code="chat.use"),
            UserRole(tenant_id="tenant-a", user_id="alice", role_id="employee"),
            User(tenant_id="tenant-a", id="alice", username="alice", password_hash=hasher.hash("a-secure-password"),
                 department_id="sales", authz_version=3),
        ])
        session.commit()


def test_login_builds_server_side_tenant_context(tmp_path: Path) -> None:
    database = _database(tmp_path)
    hasher = PasswordHasher(iterations=10_000)
    _seed(database, hasher)
    service = AuthenticationService(UserRepository(), hasher, TokenService("test-secret"))
    with database.session_factory() as session:
        result = service.login(session, tenant_id="tenant-a", username="alice", password="a-secure-password")
        restored = service.authenticate(session, result.access_token)
    assert restored.tenant_id == "tenant-a"
    assert restored.department_scope_ids == frozenset({"head", "sales"})
    assert restored.feature_permissions == frozenset({"chat.use"})


def test_old_token_is_revoked_after_authz_version_change(tmp_path: Path) -> None:
    database = _database(tmp_path)
    hasher = PasswordHasher(iterations=10_000)
    _seed(database, hasher)
    service = AuthenticationService(UserRepository(), hasher, TokenService("test-secret"))
    with database.session_factory() as session:
        result = service.login(session, tenant_id="tenant-a", username="alice", password="a-secure-password")
        user = session.get(User, ("tenant-a", "alice"))
        user.authz_version += 1
        session.commit()
    with database.session_factory() as session, pytest.raises(StaleAuthorizationError):
        service.authenticate(session, result.access_token)
