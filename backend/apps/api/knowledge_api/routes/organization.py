from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Department, Role, RolePermission, User, UserRole

from knowledge_api.dependencies import get_auth_service, get_session, require_permission


router = APIRouter(prefix="/api/organization", tags=["organization"])


class DepartmentRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    parent_id: str | None = None


class UserUpdateRequest(BaseModel):
    active: bool | None = None
    department_id: str | None = None


class RolePermissionsRequest(BaseModel):
    permissions: list[str] = Field(default_factory=list)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=512)
    department_id: str
    role_id: str


class RoleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=80)


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
    if payload.parent_id and session.get(Department, (context.tenant_id, payload.parent_id)) is None:
        raise HTTPException(status_code=404, detail="parent department not found")
    row = Department(tenant_id=context.tenant_id, id=str(uuid4()), parent_id=payload.parent_id, name=payload.name, status="active")
    session.add(row)
    session.commit()
    return {"id": row.id, "parent_id": row.parent_id, "name": row.name, "status": row.status}


@router.get("/users")
def list_users(context: AccessContext = Depends(require_permission("organization.read")), session: Session = Depends(get_session)) -> list[dict]:
    rows = session.scalars(select(User).where(User.tenant_id == context.tenant_id).order_by(User.username)).all()
    departments = {d.id: d.name for d in session.scalars(select(Department).where(Department.tenant_id == context.tenant_id)).all()}
    role_names: dict[str, str] = {}
    for link in session.scalars(select(UserRole).where(UserRole.tenant_id == context.tenant_id)).all():
        role = session.get(Role, (context.tenant_id, link.role_id))
        if role and link.user_id not in role_names: role_names[link.user_id] = role.name
    return [{"id": r.id, "username": r.username, "department_id": r.department_id, "department": departments.get(r.department_id, ""), "role": role_names.get(r.id, "未分配"), "active": r.active} for r in rows]


@router.patch("/users/{user_id}")
def update_user(user_id: str, payload: UserUpdateRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session)) -> dict:
    row = session.get(User, (context.tenant_id, user_id))
    if row is None: raise HTTPException(status_code=404, detail="user not found")
    if payload.active is False and row.id == context.user_id:
        raise HTTPException(status_code=400, detail="cannot deactivate current user")
    if payload.active is not None: row.active = payload.active
    if payload.department_id is not None:
        if session.get(Department, (context.tenant_id, payload.department_id)) is None: raise HTTPException(status_code=404, detail="department not found")
        row.department_id = payload.department_id
    row.authz_version += 1
    session.commit()
    return {"id": row.id, "active": row.active, "department_id": row.department_id, "authz_version": row.authz_version}


@router.post("/users")
def create_user(payload: UserCreateRequest, context: AccessContext = Depends(require_permission("organization.admin")), session: Session = Depends(get_session), auth_service=Depends(get_auth_service)) -> dict:
    if session.scalar(select(User).where(User.tenant_id == context.tenant_id, User.username == payload.username)):
        raise HTTPException(status_code=409, detail="username already exists")
    if session.get(Department, (context.tenant_id, payload.department_id)) is None: raise HTTPException(status_code=404, detail="department not found")
    if session.get(Role, (context.tenant_id, payload.role_id)) is None: raise HTTPException(status_code=404, detail="role not found")
    row = User(tenant_id=context.tenant_id, id=str(uuid4()), username=payload.username, password_hash=auth_service.passwords.hash(payload.password), department_id=payload.department_id, authz_version=1, active=True)
    session.add(row); session.flush(); session.add(UserRole(tenant_id=context.tenant_id, user_id=row.id, role_id=payload.role_id)); session.commit()
    return {"id": row.id, "username": row.username, "department_id": row.department_id, "active": row.active}


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
