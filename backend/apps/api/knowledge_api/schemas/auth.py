from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=36)
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=512)


class IdentityResponse(BaseModel):
    user_id: str
    tenant_id: str
    department_id: str
    role_ids: list[str]
    permissions: list[str]
    authz_version: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    identity: IdentityResponse
