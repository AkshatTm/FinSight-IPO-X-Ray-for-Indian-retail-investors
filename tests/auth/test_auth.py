"""B1.2: Supabase JWT checks (HS256 fallback and JWKS) and the offline user."""

from __future__ import annotations

import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from finsight.auth import LOCAL_USER_ID, AuthError, user_from_header, verify_token
from finsight.core.config import AuthConfig

URL = "https://abc.supabase.co"
SECRET = "test-secret-not-real-" + "x" * 20
CFG = AuthConfig(
    mode="supabase", supabase_url=URL, jwt_secret=SECRET, admin_emails=["akshat@example.com"]
)


def _claims(**over: Any) -> dict[str, Any]:
    base = {
        "sub": "user-1",
        "email": "akshat@example.com",
        "aud": "authenticated",
        "iss": f"{URL}/auth/v1",
        "exp": int(time.time()) + 600,
    }
    return {**base, **over}


def test_valid_hs256_token() -> None:
    token = jwt.encode(_claims(), SECRET, algorithm="HS256")
    user = user_from_header(f"Bearer {token}", CFG)
    assert (user.id, user.email, user.is_admin) == ("user-1", "akshat@example.com", True)


@pytest.mark.parametrize(
    "claims",
    [
        _claims(aud="anon"),
        _claims(iss="https://evil.example/auth/v1"),
        _claims(exp=int(time.time()) - 10),
    ],
)
def test_wrong_audience_issuer_or_expired(claims: dict[str, Any]) -> None:
    with pytest.raises(AuthError):
        verify_token(jwt.encode(claims, SECRET, algorithm="HS256"), CFG)


def test_wrong_secret_and_garbage() -> None:
    with pytest.raises(AuthError):
        verify_token(jwt.encode(_claims(), "other-secret-" + "y" * 30, algorithm="HS256"), CFG)
    with pytest.raises(AuthError):
        verify_token("not-a-jwt", CFG)
    with pytest.raises(AuthError):
        user_from_header(None, CFG)


class _FakeJwks:
    def __init__(self, public_key: Any) -> None:
        self.key = public_key

    def get_signing_key_from_jwt(self, token: str) -> Any:
        return self


def test_es256_token_checked_against_jwks() -> None:
    private = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(_claims(email="someone@example.com"), private, algorithm="ES256")
    claims = verify_token(token, CFG, jwks=_FakeJwks(private.public_key()))  # type: ignore[arg-type]
    assert claims["sub"] == "user-1"
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(AuthError):
        verify_token(token, CFG, jwks=_FakeJwks(other.public_key()))  # type: ignore[arg-type]


def test_auth_off_is_one_local_user() -> None:
    assert user_from_header(None, AuthConfig()).id == LOCAL_USER_ID
