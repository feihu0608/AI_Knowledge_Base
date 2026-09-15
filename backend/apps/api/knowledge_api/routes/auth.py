from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from knowledge_application.auth_service import AuthenticationError, AuthenticationService
from knowledge_domain.authorization.models import AccessContext

from knowledge_api.dependencies import get_access_context, get_auth_service, get_session
from knowledge_api.schemas.auth import IdentityResponse, LoginRequest, LoginResponse


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _identity(context: AccessContext) -> IdentityResponse:
    return IdentityResponse(
        user_id=context.user_id, tenant_id=context.tenant_id, department_id=context.department_id,
        role_ids=sorted(context.role_ids), permissions=sorted(context.feature_permissions),
        authz_version=context.authz_version,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session),
          service: AuthenticationService = Depends(get_auth_service)) -> LoginResponse:
    try:
        result = service.login(session, tenant_id=payload.tenant_id, username=payload.username, password=payload.password)
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials") from exc
    return LoginResponse(access_token=result.access_token, expires_at=result.expires_at, identity=_identity(result.context))


@router.get("/me", response_model=IdentityResponse)
def me(context: AccessContext = Depends(get_access_context)) -> IdentityResponse:
    return _identity(context)
