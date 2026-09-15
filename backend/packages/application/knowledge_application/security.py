from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import base64
import hashlib
import hmac
import os
from typing import Any
from uuid import uuid4

import jwt


class InvalidTokenError(ValueError):
    pass


class PasswordHasher:
    algorithm = "pbkdf2_sha256"

    def __init__(self, iterations: int = 600_000) -> None:
        self.iterations = iterations

    def hash(self, password: str) -> str:
        if len(password) < 10:
            raise ValueError("password must contain at least 10 characters")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, self.iterations)
        return "$".join(
            [self.algorithm, str(self.iterations), base64.b64encode(salt).decode(), base64.b64encode(digest).decode()]
        )

    def verify(self, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations, salt_text, expected_text = encoded.split("$", 3)
            if algorithm != self.algorithm:
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), base64.b64decode(salt_text), int(iterations)
            )
            return hmac.compare_digest(actual, base64.b64decode(expected_text))
        except (ValueError, TypeError):
            return False


@dataclass(frozen=True, slots=True)
class IdentityClaims:
    user_id: str
    tenant_id: str
    department_id: str
    authz_version: int
    role_ids: tuple[str, ...]
    permissions: tuple[str, ...]


class TokenService:
    def __init__(self, secret: str, algorithm: str = "HS256", access_minutes: int = 30) -> None:
        self.secret = secret
        self.algorithm = algorithm
        self.access_minutes = access_minutes

    def issue_access_token(self, identity: IdentityClaims) -> tuple[str, datetime]:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self.access_minutes)
        claims: dict[str, Any] = {
            "sub": identity.user_id,
            "tid": identity.tenant_id,
            "dept": identity.department_id,
            "aver": identity.authz_version,
            "roles": list(identity.role_ids),
            "permissions": list(identity.permissions),
            "type": "access",
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
        }
        return jwt.encode(claims, self.secret, algorithm=self.algorithm), expires_at

    def decode_access_token(self, token: str) -> IdentityClaims:
        try:
            claims = jwt.decode(token, self.secret, algorithms=[self.algorithm], options={"require": ["exp", "sub", "tid"]})
            if claims.get("type") != "access":
                raise InvalidTokenError("wrong token type")
            return IdentityClaims(
                user_id=str(claims["sub"]),
                tenant_id=str(claims["tid"]),
                department_id=str(claims["dept"]),
                authz_version=int(claims["aver"]),
                role_ids=tuple(str(item) for item in claims.get("roles", [])),
                permissions=tuple(str(item) for item in claims.get("permissions", [])),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError("invalid or expired access token") from exc
