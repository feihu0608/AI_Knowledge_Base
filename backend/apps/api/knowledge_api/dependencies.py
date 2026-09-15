from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from knowledge_application.auth_service import AuthenticationError, AuthenticationService
from knowledge_application.ingestion_service import IngestionApplicationService
from knowledge_application.chat_service import ChatApplicationService
from knowledge_application.security import InvalidTokenError
from knowledge_domain.authorization.models import AccessContext


bearer = HTTPBearer(auto_error=False)


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.database.session_factory() as session:
        yield session


def get_auth_service(request: Request) -> AuthenticationService:
    return request.app.state.auth_service


def get_ingestion_service(request: Request) -> IngestionApplicationService:
    return request.app.state.ingestion_service


def get_chat_service(request: Request) -> ChatApplicationService:
    return request.app.state.chat_service


def get_access_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> AccessContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication required")
    try:
        return service.authenticate(session, credentials.credentials)
    except (AuthenticationError, InvalidTokenError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


def require_permission(permission: str):
    def dependency(context: AccessContext = Depends(get_access_context)) -> AccessContext:
        if permission not in context.feature_permissions:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        return context
    return dependency
