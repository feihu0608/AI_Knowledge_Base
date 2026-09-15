from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Department, DepartmentClosure, Role, RolePermission, User, UserRole

from knowledge_api.dependencies import get_auth_service, get_session, require_permission


router = APIRouter(prefix="/api/organization", tags=["organization"])


class DepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None


class UserUpdateRequest(BaseModel):
    active: bool | None = None
    department_id: str | None = None
    role_id: str | None = None


class RolePermissionsRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=512)
    department_id: str = Field(min_length=1, max_length=36)
    role_id: str = Field(min_length=1, max_length=36)


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=80)


def _required_text(value: str | None, field_name: str) -> str:
    """Normalize user supplied identifiers while keeping passwords untouched."""
    normalized = (value or "").strip()
    if not normalized:
        raise HTTPException(status_code=422, detail=f"{field_name}不能为空")
    return normalized


def _same_level_department(
    session: Session, *, tenant_id: str, parent_id: str | None, name: str
) -> Department | None:
    statement = select(Department).where(
        Department.tenant_id == tenant_id,
        func.lower(Department.name) == name.casefold(),
    )
    if parent_id is None:
        statement = statement.where(Department.parent_id.is_(None))
    else:
        statement = statement.where(Department.parent_id == parent_id)
    return session.scalar(statement)


@router.get("/departments")
def list_departments(
    context: AccessContext = Depends(require_permission("organization.read")),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.scalars(
        select(Department).where(Department.tenant_id == context.tenant_id).order_by(Department.name)
    ).all()
    return [{"id": row.id, "parent_id": row.parent_id, "name": row.name, "status": row.status} for row in rows]


@router.post("/departments")
def create_department(payload: DepartmentRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    name = _required_text(payload.name, "部门名称")
    parent_id = (payload.parent_id or "").strip() or None
    if parent_id and session.get(Department, (context.tenant_id, parent_id)) is None:
        raise HTTPException(status_code=404, detail="parent department not found")
    if _same_level_department(session, tenant_id=context.tenant_id, parent_id=parent_id, name=name):
        raise HTTPException(status_code=409, detail="同一上级部门下已存在同名部门")

    row = Department(tenant_id=context.tenant_id, id=str(uuid4()), parent_id=parent_id, name=name, status="active")
    try:
        session.add(row)
        # Flush the department before inserting closure rows because both closure
        # foreign keys point to the newly created department.
        session.flush()
        ancestors = (
            session.scalars(
                select(DepartmentClosure).where(
                    DepartmentClosure.tenant_id == context.tenant_id,
                    DepartmentClosure.descendant_id == parent_id,
                )
            ).all()
            if parent_id
            else []
        )
        # A legacy database may have a department without its reflexive closure.
        # Repair that single missing edge so new descendants still get a complete
        # authorization path.
        if parent_id and not any(item.ancestor_id == parent_id for item in ancestors):
            parent_self = DepartmentClosure(
                tenant_id=context.tenant_id,
                ancestor_id=parent_id,
                descendant_id=parent_id,
                depth=0,
            )
            ancestors.append(parent_self)
            session.add(parent_self)
        session.add(DepartmentClosure(tenant_id=context.tenant_id, ancestor_id=row.id, descendant_id=row.id, depth=0))
        for ancestor in ancestors:
            session.add(
                DepartmentClosure(
                    tenant_id=context.tenant_id,
                    ancestor_id=ancestor.ancestor_id,
                    descendant_id=row.id,
                    depth=ancestor.depth + 1,
                )
            )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # The pre-check closes the normal path; this also handles two admins
        # creating the same sibling concurrently without returning HTTP 500.
        raise HTTPException(status_code=409, detail="部门保存冲突，请检查同级名称和上级部门") from exc
    return {"id": row.id, "parent_id": row.parent_id, "name": row.name, "status": row.status}


@router.get("/users")
def list_users(context: AccessContext = Depends(require_permission("organization.read")), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(User).where(User.tenant_id == context.tenant_id).order_by(User.username)).all()
    departments = {d.id: d.name for d in session.scalars(select(Department).where(Department.tenant_id == context.tenant_id)).all()}
    role_names: dict[str, str] = {}
    role_ids: dict[str, list[str]] = {}
    for link in session.scalars(select(UserRole).where(UserRole.tenant_id == context.tenant_id)).all():
        role = session.get(Role, (context.tenant_id, link.role_id))
        if role:
            role_ids.setdefault(link.user_id, []).append(role.id)
            if link.user_id not in role_names:
                role_names[link.user_id] = role.name
    return [
        {
            "id": r.id,
            "username": r.username,
            "department_id": r.department_id,
            "department": departments.get(r.department_id, ""),
            "role": role_names.get(r.id, "未分配"),
            "role_id": (role_ids.get(r.id) or [None])[0],
            "role_ids": sorted(role_ids.get(r.id, [])),
            "active": r.active,
        }
        for r in rows
    ]


@router.patch("/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    row = session.get(User, (context.tenant_id, user_id))
    if row is None: raise HTTPException(status_code=404, detail="user not found")
    if payload.active is False and row.id == context.user_id:
        raise HTTPException(status_code=400, detail="cannot deactivate current user")
    changed = False
    if payload.active is not None and payload.active != row.active:
        row.active = payload.active
        changed = True
    if payload.department_id is not None:
        department_id = _required_text(payload.department_id, "部门")
        if session.get(Department, (context.tenant_id, department_id)) is None:
            raise HTTPException(status_code=404, detail="department not found")
        if department_id != row.department_id:
            row.department_id = department_id
            changed = True
    if payload.role_id is not None:
        role_id = _required_text(payload.role_id, "角色")
        if session.get(Role, (context.tenant_id, role_id)) is None:
            raise HTTPException(status_code=404, detail="role not found")
        current_role_ids = set(
            session.scalars(
                select(UserRole.role_id).where(
                    UserRole.tenant_id == context.tenant_id,
                    UserRole.user_id == row.id,
                )
            ).all()
        )
        if current_role_ids != {role_id}:
            session.execute(
                delete(UserRole).where(
                    UserRole.tenant_id == context.tenant_id,
                    UserRole.user_id == row.id,
                )
            )
            session.add(UserRole(tenant_id=context.tenant_id, user_id=row.id, role_id=role_id))
            changed = True
    if changed:
        row.authz_version += 1
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="用户更新冲突，请刷新后重试") from exc
    return {"id": row.id, "active": row.active, "department_id": row.department_id, "authz_version": row.authz_version}


@router.post("/users")
def create_user(payload: UserCreateRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session), auth_service=Depends(get_auth_service)) -> dict:
    username = _required_text(payload.username, "账号")
    department_id = _required_text(payload.department_id, "部门")
    role_id = _required_text(payload.role_id, "角色")
    if session.scalar(
        select(User).where(
            User.tenant_id == context.tenant_id,
            func.lower(User.username) == username.casefold(),
        )
    ):
        raise HTTPException(status_code=409, detail="username already exists")
    if session.get(Department, (context.tenant_id, department_id)) is None:
        raise HTTPException(status_code=404, detail="department not found")
    if session.get(Role, (context.tenant_id, role_id)) is None:
        raise HTTPException(status_code=404, detail="role not found")
    row = User(
        tenant_id=context.tenant_id,
        id=str(uuid4()),
        username=username,
        password_hash=auth_service.passwords.hash(payload.password),
        department_id=department_id,
        authz_version=1,
        active=True,
    )
    try:
        session.add(row)
        session.flush()
        session.add(UserRole(tenant_id=context.tenant_id, user_id=row.id, role_id=role_id))
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="用户保存冲突，请检查账号是否已存在") from exc
    return {"id": row.id, "username": row.username, "department_id": row.department_id, "role_id": role_id, "active": row.active}


@router.get("/roles")
def list_roles(context: AccessContext = Depends(require_permission("organization.read")), session: Session = Depends(get_session)) -> list[dict]:
    roles = session.scalars(select(Role).where(Role.tenant_id == context.tenant_id).order_by(Role.name)).all()
    permissions = session.scalars(select(RolePermission).where(RolePermission.tenant_id == context.tenant_id)).all()
    by_role: dict[str, list[str]] = {}
    for p in permissions: by_role.setdefault(p.role_id, []).append(p.permission_code)
    return [{"id": r.id, "code": r.code, "name": r.name, "permissions": sorted(by_role.get(r.id, []))} for r in roles]


@router.post("/roles")
def create_role(payload: RoleCreateRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    if session.scalar(select(Role).where(Role.tenant_id == context.tenant_id, Role.code == payload.code)):
        raise HTTPException(status_code=409, detail="role code already exists")
    row = Role(tenant_id=context.tenant_id, id=str(uuid4()), code=payload.code, name=payload.name)
    session.add(row); session.commit(); return {"id": row.id, "code": row.code, "name": row.name, "permissions": []}


@router.put("/roles/{role_id}/permissions")
def update_role_permissions(role_id: str, payload: RolePermissionsRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    role = session.get(Role, (context.tenant_id, role_id))
    if role is None: raise HTTPException(status_code=404, detail="role not found")
    existing = session.scalars(select(RolePermission).where(RolePermission.tenant_id == context.tenant_id, RolePermission.role_id == role_id)).all()
    for row in existing: session.delete(row)
    for code in sorted(set(payload.permissions)):
        session.add(RolePermission(tenant_id=context.tenant_id, role_id=role_id, permission_code=code))
    session.commit()
    return {"id": role.id, "permissions": sorted(set(payload.permissions))}


@router.delete("/roles/{role_id}")
def delete_role(role_id: str, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    role = session.get(Role, (context.tenant_id, role_id))
    if role is None:
        raise HTTPException(status_code=404, detail="role not found")
    if session.scalar(select(UserRole).where(UserRole.tenant_id == context.tenant_id, UserRole.role_id == role_id)):
        raise HTTPException(status_code=409, detail="角色仍被用户使用，请先调整用户角色")
    for permission in session.scalars(select(RolePermission).where(RolePermission.tenant_id == context.tenant_id, RolePermission.role_id == role_id)).all():
        session.delete(permission)
    session.delete(role)
    session.commit()
    return {"id": role_id, "deleted": True}
