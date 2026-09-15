from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from sqlalchemy import select


BACKEND = Path(__file__).resolve().parents[1]
for package in ("domain", "application", "persistence"):
    sys.path.insert(0, str(BACKEND / "packages" / package))

from knowledge_application.security import PasswordHasher  # noqa: E402
from knowledge_persistence import Base, Database  # noqa: E402
from knowledge_persistence.models import (  # noqa: E402
    Department, DepartmentClosure, FaqCandidate, FaqItem, KnowledgeBase, KnowledgeGap,
    Role, RolePermission, Tenant, User, UserRole,
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
            root_id, child_id, role_id = f"{tenant_id}-root", f"{tenant_id}-rd", f"{tenant_id}-admin"
            if session.get(Tenant, tenant_id) is None:
                session.add(Tenant(id=tenant_id, name=tenant_name)); session.flush()
                session.add_all([Department(tenant_id=tenant_id, id=root_id, parent_id=None, name="总部"), Department(tenant_id=tenant_id, id=child_id, parent_id=root_id, name="研发部")]); session.flush()
                session.add_all([DepartmentClosure(tenant_id=tenant_id, ancestor_id=root_id, descendant_id=root_id, depth=0), DepartmentClosure(tenant_id=tenant_id, ancestor_id=root_id, descendant_id=child_id, depth=1), DepartmentClosure(tenant_id=tenant_id, ancestor_id=child_id, descendant_id=child_id, depth=0), Role(tenant_id=tenant_id, id=role_id, code="tenant_admin", name="租户管理员"), User(tenant_id=tenant_id, id=user_id, username=username, password_hash=hasher.hash(password), department_id=child_id, authz_version=1, active=True), KnowledgeBase(tenant_id=tenant_id, id=kb_id, name=kb_name, enabled=True)]); session.flush()
                session.add_all([UserRole(tenant_id=tenant_id, user_id=user_id, role_id=role_id), *[RolePermission(tenant_id=tenant_id, role_id=role_id, permission_code=code) for code in ADMIN_PERMISSIONS]])
            # Idempotent organization fixtures: these are deliberately fictional and safe to re-run.
            department_fixtures = (
                (f"{tenant_id}-sales", root_id, "销售部"),
                (f"{tenant_id}-ops", root_id, "运营部"),
                (f"{tenant_id}-qa", child_id, "质量保障组"),
                (f"{tenant_id}-platform", child_id, "平台工程组"),
            )
            for department_id, parent_id, name in department_fixtures:
                if session.get(Department, (tenant_id, department_id)) is None:
                    session.add(Department(tenant_id=tenant_id, id=department_id, parent_id=parent_id, name=name, status="active"))
                    session.flush()
                    session.add(DepartmentClosure(tenant_id=tenant_id, ancestor_id=department_id, descendant_id=department_id, depth=0))
                    ancestors = session.scalars(select(DepartmentClosure).where(DepartmentClosure.tenant_id == tenant_id, DepartmentClosure.descendant_id == parent_id)).all()
                    session.add_all([DepartmentClosure(tenant_id=tenant_id, ancestor_id=a.ancestor_id, descendant_id=department_id, depth=a.depth + 1) for a in ancestors])
            role_fixtures = (
                (f"{tenant_id}-analyst", "data_analyst", "数据分析员", ("organization.read", "knowledge.read", "chat.use")),
                (f"{tenant_id}-reviewer", "knowledge_reviewer", "知识库审核员", ("organization.read", "knowledge.read", "knowledge.write", "faq.review")),
            )
            for fixture_id, code, name, permissions in role_fixtures:
                if session.get(Role, (tenant_id, fixture_id)) is None:
                    session.add(Role(tenant_id=tenant_id, id=fixture_id, code=code, name=name))
                    session.flush()
                    session.add_all([RolePermission(tenant_id=tenant_id, role_id=fixture_id, permission_code=p) for p in permissions])
            user_fixtures = (
                (f"{tenant_id}-sales-user", f"{username}_sales", f"{tenant_id}-sales", f"{tenant_id}-analyst", True),
                (f"{tenant_id}-ops-user", f"{username}_ops", f"{tenant_id}-ops", f"{tenant_id}-reviewer", True),
                (f"{tenant_id}-qa-user", f"{username}_qa", f"{tenant_id}-qa", f"{tenant_id}-analyst", False),
            )
            for fixture_id, fixture_username, department_id, fixture_role_id, active in user_fixtures:
                if session.get(User, (tenant_id, fixture_id)) is None:
                    session.add(User(tenant_id=tenant_id, id=fixture_id, username=fixture_username, password_hash=hasher.hash(password), department_id=department_id, authz_version=1, active=active))
                    session.flush()
                    session.add(UserRole(tenant_id=tenant_id, user_id=fixture_id, role_id=fixture_role_id))
            if session.scalar(select(FaqCandidate.id).where(FaqCandidate.tenant_id == tenant_id)) is None:
                session.add_all([
                    FaqCandidate(tenant_id=tenant_id, id=f"{tenant_id}-faq-001", state="draft", representative_question="差旅报销需要哪些材料？", proposed_answer="请提供发票、行程单及审批单，按差旅制度提交至费用系统。", frequency=186, unique_users=94),
                    FaqCandidate(tenant_id=tenant_id, id=f"{tenant_id}-faq-002", state="draft", representative_question="如何申请远程办公 VPN？", proposed_answer="在 IT 服务台提交远程办公申请，审批通过后按指引安装客户端。", frequency=142, unique_users=76),
                ])
            if session.scalar(select(FaqItem.id).where(FaqItem.tenant_id == tenant_id)) is None:
                session.add(FaqItem(tenant_id=tenant_id, id=f"{tenant_id}-published-001", version=1, status="enabled", question="忘记密码如何处理？", answer="联系 IT 服务台核验身份后重置密码。", acl_version=1))
            if session.scalar(select(KnowledgeGap.id).where(KnowledgeGap.tenant_id == tenant_id)) is None:
                session.add_all([KnowledgeGap(tenant_id=tenant_id, id=f"{tenant_id}-gap-001", reason="low_confidence", representative_question="海外出差的保险如何购买？", frequency=31, status="open"), KnowledgeGap(tenant_id=tenant_id, id=f"{tenant_id}-gap-002", reason="no_hit", representative_question="研发设备报废审批在哪个系统？", frequency=18, status="open")])
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
