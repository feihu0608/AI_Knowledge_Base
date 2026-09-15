from knowledge_application.security import IdentityClaims, InvalidTokenError, PasswordHasher, TokenService


def test_password_hash_is_salted_and_verifiable() -> None:
    hasher = PasswordHasher(iterations=10_000)
    first = hasher.hash("correct-horse-battery")
    second = hasher.hash("correct-horse-battery")
    assert first != second
    assert hasher.verify("correct-horse-battery", first)
    assert not hasher.verify("wrong-password", first)


def test_access_token_preserves_tenant_and_authz_version() -> None:
    tokens = TokenService("test-secret-with-sufficient-entropy", access_minutes=5)
    identity = IdentityClaims("user-1", "tenant-a", "dept-sales", 7, ("role-a",), ("chat.use",))
    token, _ = tokens.issue_access_token(identity)
    assert tokens.decode_access_token(token) == identity


def test_rejects_token_signed_by_another_secret() -> None:
    token, _ = TokenService("first-secret").issue_access_token(
        IdentityClaims("user-1", "tenant-a", "dept-a", 1, (), ())
    )
    try:
        TokenService("second-secret").decode_access_token(token)
    except InvalidTokenError:
        pass
    else:
        raise AssertionError("foreign token must be rejected")
