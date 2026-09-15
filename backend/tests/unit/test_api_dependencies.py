import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from knowledge_api.dependencies import get_access_context
from knowledge_application.security import InvalidTokenError


class ExpiredTokenService:
    def authenticate(self, session, token):
        raise InvalidTokenError("invalid or expired access token")


def test_expired_access_token_is_reported_as_401() -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired")
    with pytest.raises(HTTPException) as error:
        get_access_context(credentials=credentials, session=object(), service=ExpiredTokenService())
    assert error.value.status_code == 401
    assert error.value.detail == "invalid or expired access token"
