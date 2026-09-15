from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from knowledge_api.main import create_app
from knowledge_application.config import Settings
from knowledge_application.security import PasswordHasher
from knowledge_persistence import Base, Database
from knowledge_persistence.models import (
    Department,
    DepartmentClosure,
    Role,
    RolePermission,
    Tenant,
    User,
    UserRole,
)


def _client(tmp_path: Path) -> tuple[TestClient, Database]:
    database = Database(f"sqlite:///{tmp_path / 'organization.db'}")
    Base.metadata.create_all(database.engine)
    hasher = PasswordHasher(iterations=10_000)
    with database.session_factory() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="组织回归租户"),
                Department(tenant_id="tenant-a", id="head", parent_id=None, name="总部"),
                Department(tenant_id="tenant-a", id="sales", parent_id="head", name="销售部"),
                DepartmentClosure(tenant_id="tenant-a", ancestor_id="head", descendant_id="head", depth=0),
                DepartmentClosure(tenant_id="tenant-a", ancestor_id="head", descendant_id="sales", depth=1),
                DepartmentClosure(tenant_id="tenant-a", ancestor_id="sales", descendant_id="sales", depth=0),
                Role(tenant_id="tenant-a", id="admin-role", code="admin", name="管理员"),
                Role(tenant_id="tenant-a", id="staff-role", code="staff", name="员工"),
                RolePermission(tenant_id="tenant-a", role_id="admin-role", permission_code="organization.read"),
                RolePermission(tenant_id="tenant-a", role_id="admin-role", permission_code="organization.admin"),
                User(tenant_id="tenant-a", id="admin", username="admin", password_hash=hasher.hash("a-secure-password"), department_id="sales", authz_version=1, active=True),
                UserRole(tenant_id="tenant-a", user_id="admin", role_id="admin-role"),
            ]
        )
        session.commit()
    app = create_app(
        Settings(database_url=f"sqlite:///{tmp_path / 'organization.db'}", jwt_secret="test-secret"),
        database,
    )
    client = TestClient(app)
    login = client.post(
        "/api/auth/login",
        json={"tenant_id": "tenant-a", "username": "admin", "password": "a-secure-password"},
    )
    assert login.status_code == 200, login.text
    client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    return client, database


def test_department_duplicate_is_conflict_and_closure_is_complete(tmp_path: Path) -> None:
    client, database = _client(tmp_path)
    try:
        created = client.post("/api/organization/departments", json={"name": "平台组", "parent_id": "sales"})
        assert created.status_code == 200, created.text
        duplicate = client.post("/api/organization/departments", json={"name": "平台组", "parent_id": "sales"})
        assert duplicate.status_code == 409
        assert "同名" in duplicate.json()["detail"]

        department_id = created.json()["id"]
        child = client.post(
            "/api/organization/departments", json={"name": "平台子组", "parent_id": department_id}
        )
        assert child.status_code == 200, child.text
        with database.session_factory() as session:
            closure = session.scalars(
                select(DepartmentClosure).where(
                    DepartmentClosure.tenant_id == "tenant-a",
                    DepartmentClosure.descendant_id == child.json()["id"],
                )
            ).all()
            assert {(item.ancestor_id, item.depth) for item in closure} == {
                ("head", 3),
                ("sales", 2),
                (department_id, 1),
                (child.json()["id"], 0),
            }
    finally:
        client.close()
        database.engine.dispose()


def test_user_create_defaults_are_validated_and_edit_persists_department_and_role(tmp_path: Path) -> None:
    client, database = _client(tmp_path)
    try:
        bad = client.post(
            "/api/organization/users",
            json={"username": "new-user", "password": "a-secure-password", "department_id": "", "role_id": ""},
        )
        assert bad.status_code == 422

        created = client.post(
            "/api/organization/users",
            json={
                "username": "new-user",
                "password": "a-secure-password",
                "department_id": "sales",
                "role_id": "staff-role",
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["role_id"] == "staff-role"
        user_id = created.json()["id"]

        updated = client.patch(
            f"/api/organization/users/{user_id}",
            json={"department_id": "head", "role_id": "admin-role"},
        )
        assert updated.status_code == 200, updated.text
        users = client.get("/api/organization/users")
        assert users.status_code == 200
        row = next(item for item in users.json() if item["id"] == user_id)
        assert row["department_id"] == "head"
        assert row["role_id"] == "admin-role"
        assert row["role_ids"] == ["admin-role"]
    finally:
        client.close()
        database.engine.dispose()
