"""Who is calling: verify Supabase JWTs (JWKS with an HS256 fallback), or one local user offline.

B06 §1: the token's ``aud`` must be ``authenticated`` and ``iss`` must be the project's
``<supabase_url>/auth/v1``. With ``auth.mode: off`` (laptop) every caller is ``local-dev``.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt

from finsight.core.config import AuthConfig

LOCAL_USER_ID = "local-dev"


@dataclass(frozen=True)
class User:
    """The signed-in user: Supabase user id, email and admin flag."""

    id: str
    email: str | None = None
    is_admin: bool = False


class AuthError(Exception):
    """The token is missing or invalid (API: 401 ``unauthorized``)."""


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def _issuer(cfg: AuthConfig) -> str:
    return f"{(cfg.supabase_url or '').rstrip('/')}/auth/v1"


def verify_token(
    token: str, cfg: AuthConfig, jwks: jwt.PyJWKClient | None = None
) -> dict[str, Any]:
    """Return the token's claims, or raise ``AuthError``.

    Asymmetric tokens (RS256/ES256) are checked against the project's JWKS; HS256 tokens need
    ``auth.jwt_secret`` (projects that still use the legacy shared secret).
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as err:
        raise AuthError("malformed token") from err
    alg = header.get("alg", "")
    try:
        if alg == "HS256":
            if not cfg.jwt_secret:
                raise AuthError("HS256 token but no FINSIGHT_AUTH__JWT_SECRET")
            key: Any = cfg.jwt_secret
        elif alg in ("RS256", "ES256"):
            client = jwks or _jwks_client(f"{_issuer(cfg)}/.well-known/jwks.json")
            key = client.get_signing_key_from_jwt(token).key
        else:
            raise AuthError(f"unsupported alg {alg!r}")
        claims: dict[str, Any] = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience=cfg.audience,
            issuer=_issuer(cfg),
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
    except jwt.PyJWTError as err:
        raise AuthError(type(err).__name__) from err
    return claims


def user_from_header(authorization: str | None, cfg: AuthConfig) -> User:
    """The caller for an ``Authorization: Bearer …`` header (``AuthError`` when not allowed)."""
    if cfg.mode == "off":
        return User(LOCAL_USER_ID, None, is_admin=True)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("missing bearer token")
    claims = verify_token(authorization[7:].strip(), cfg)
    email = claims.get("email")
    admins = {a.lower() for a in cfg.admin_emails}
    return User(str(claims["sub"]), email, is_admin=bool(email and email.lower() in admins))


__all__ = ["LOCAL_USER_ID", "AuthError", "User", "user_from_header", "verify_token"]
