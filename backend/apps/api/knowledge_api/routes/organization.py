from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.models import Department

from knowledge_api.dependencies import get_session, require_permission


router = APIRouter(prefix="/api/organization", tags=["organization"])


@router.get("/departments")
def list_departments(
    context: AccessContext = Depends(require_permission("organization.read")),
    session: Session = Depends(get_session),
) -> list[dict]:
    rows = session.scalars(
        select(Department).where(Department.tenant_id == context.tenant_id).order_by(Department.name)
    ).all()
    return [{"id": row.id, "parent_id": row.parent_id, "name": row.name, "status": row.status} for row in rows]
