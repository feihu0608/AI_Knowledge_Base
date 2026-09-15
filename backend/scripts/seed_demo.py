from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


BACKEND = Path(__file__).resolve().parents[1]
for package in ("domain", "application", "persistence"):
    sys.path.insert(0, str(BACKEND / "packages" / package))

from knowledge_application.security import PasswordHasher  # noqa: E402
from knowledge_persistence import Base, Database  # noqa: E402
from knowledge_persistence.models import (  # noqa: E402
    Department, DepartmentClosure, KnowledgeBase, Role, RolePermission, Tenant, User, UserRole,
)


TENANTS = (
    ("demo-acme", "虚构演示-远航科技", "admin_acme", "acme-admin", "kb-acme", "企业制度库"),
    ("demo-bravo", "虚构演示-青禾制造", "admin_bravo", "bravo-admin", "kb-bravo", "生产知识库"),
)
ADMIN_PERMISSIONS = (
    "organization.read", "organization.admin", "knowledge.read", "knowledge.write",
    "knowledge.admin", "chat.use", "faq.review", "audit.read",
)


def seed(database_url: str, password: str, *, create_schema: bool) -> None:
    database = Database(database_url)
    if create_schema:
        Base.metadata.create_all(database.engine)
    hasher = PasswordHasher()
    with database.session_factory() as session:
        for tenant_id, tenant_name, username, user_id, kb_id, kb_name in TENANTS:
            if session.get(Tenant, tenant_id) is not None:
                continue
            root_id, child_id, role_id = f"{tenant_id}-root", f"{tenant_id}-rd", f"{tenant_id}-admin"
            session.add_all([
                Tenant(id=tenant_id, name=tenant_name),
                Department(tenant_id=tenant_id, id=root_id, parent_id=None, name="总部"),
                Department(tenant_id=tenant_id, id=child_id, parent_id=root_id, name="研发部"),
                DepartmentClosure(tenant_id=tenant_id, ancestor_id=root_id, descendant_id=root_id, depth=0),
                DepartmentClosure(tenant_id=tenant_id, ancestor_id=root_id, descendant_id=child_id, depth=1),
                DepartmentClosure(tenant_id=tenant_id, ancestor_id=child_id, descendant_id=child_id, depth=0),
                Role(tenant_id=tenant_id, id=role_id, code="tenant_admin", name="租户管理员"),
                User(tenant_id=tenant_id, id=user_id, username=username, password_hash=hasher.hash(password),
                     department_id=child_id, authz_version=1, active=True),
                UserRole(tenant_id=tenant_id, user_id=user_id, role_id=role_id),
                KnowledgeBase(tenant_id=tenant_id, id=kb_id, name=kb_name, enabled=True),
                *[RolePermission(tenant_id=tenant_id, role_id=role_id, permission_code=code)
                  for code in ADMIN_PERMISSIONS],
            ])
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create two isolated fictional demo tenants.")
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL", "sqlite:///./storage/knowledge.db"))
    parser.add_argument("--create-schema", action="store_true", help="Development only; production uses Alembic.")
    args = parser.parse_args()
    if os.getenv("APP_ENV") in {"production", "staging"} and args.create_schema:
        raise SystemExit("Refusing --create-schema outside development/test")
    password = os.getenv("DEMO_ADMIN_PASSWORD", "DemoOnly!2026")
    seed(args.database_url, password, create_schema=args.create_schema)
    print("DEMO_SEED_OK tenants=2 data_label=fictional")
    print("Accounts: demo-acme/admin_acme and demo-bravo/admin_bravo")
    if "DEMO_ADMIN_PASSWORD" not in os.environ:
        print("Development password: DemoOnly!2026 (change before shared deployment)")


if __name__ == "__main__":
    main()
