from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import time

from sqlalchemy.orm import Session

from knowledge_domain.authorization.models import AccessContext
from knowledge_persistence.repositories import UserIdentityRow, UserRepository

from .security import IdentityClaims, PasswordHasher, TokenService


class AuthenticationError(ValueError):
    pass


class StaleAuthorizationError(AuthenticationError):
    pass


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    expires_at: datetime
    context: AccessContext


class LoginAttemptGuard:
    """Process-local trial guard; production wiring replaces it with Redis."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 300) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}

    def check(self, key: str) -> None:
        now = time.monotonic()
        recent = [stamp for stamp in self._failures.get(key, []) if now - stamp < self.window_seconds]
        self._failures[key] = recent
        if len(recent) >= self.max_failures:
            raise AuthenticationError("too many login attempts")

    def fail(self, key: str) -> None:
        self._failures.setdefault(key, []).append(time.monotonic())

    def succeed(self, key: str) -> None:
        self._failures.pop(key, None)


class AuthenticationService:
    def __init__(self, users: UserRepository, passwords: PasswordHasher, tokens: TokenService,
                 attempts: LoginAttemptGuard | None = None) -> None:
        self.users = users
        self.passwords = passwords
        self.tokens = tokens
        self.attempts = attempts or LoginAttemptGuard()

    def login(self, session: Session, *, tenant_id: str, username: str, password: str) -> LoginResult:
        key = f"{tenant_id}:{username.casefold()}"
        self.attempts.check(key)
        identity = self.users.find_identity(session, tenant_id=tenant_id, username=username)
        if identity is None or not identity.user.active or not self.passwords.verify(password, identity.user.password_hash):
            self.attempts.fail(key)
            raise AuthenticationError("invalid credentials")
        self.attempts.succeed(key)
        context = self._context(identity)
        token, expires_at = self.tokens.issue_access_token(self._claims(context))
        return LoginResult(token, expires_at, context)

    def authenticate(self, session: Session, token: str) -> AccessContext:
        claims = self.tokens.decode_access_token(token)
        identity = self.users.get_identity(session, tenant_id=claims.tenant_id, user_id=claims.user_id)
        if identity is None or not identity.user.active:
            raise AuthenticationError("identity is inactive")
        if identity.user.authz_version != claims.authz_version:
            raise StaleAuthorizationError("authorization changed; sign in again")
        return self._context(identity)

    @staticmethod
    def _context(identity: UserIdentityRow) -> AccessContext:
        user = identity.user
        return AccessContext(
            tenant_id=user.tenant_id, user_id=user.id, department_id=user.department_id,
            ancestor_department_ids=frozenset(identity.ancestor_department_ids),
            role_ids=frozenset(identity.role_ids), feature_permissions=frozenset(identity.permissions),
            authz_version=user.authz_version, active=user.active,
        )

    @staticmethod
    def _claims(context: AccessContext) -> IdentityClaims:
        return IdentityClaims(
            user_id=context.user_id, tenant_id=context.tenant_id, department_id=context.department_id,
            authz_version=context.authz_version, role_ids=tuple(sorted(context.role_ids)),
            permissions=tuple(sorted(context.feature_permissions)),
        )
