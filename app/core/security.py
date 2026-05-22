"""Clerk JWT verification + admin allowlist guard.

Verifies session tokens issued by Clerk against the configured JWKS endpoint
and enforces an email allowlist via `settings.admin_emails`. The JWKS document
is cached in-memory with a TTL to avoid hitting Clerk on every request.
"""

from __future__ import annotations

import time
from typing import Annotated, Any

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWK, PyJWKSet

from app.core.config import get_settings

_JWKS_TTL_SECONDS = 3600
_jwks_cache: dict[str, tuple[float, PyJWKSet]] = {}

_bearer_scheme = HTTPBearer(auto_error=False)


def clear_jwks_cache() -> None:
    """Test-only: wipe the in-memory JWKS cache so each test fetches fresh."""
    _jwks_cache.clear()


async def _fetch_jwks(jwks_url: str) -> PyJWKSet:
    now = time.time()
    cached = _jwks_cache.get(jwks_url)
    if cached is not None and now - cached[0] < _JWKS_TTL_SECONDS:
        return cached[1]
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(jwks_url)
    response.raise_for_status()
    jwks = PyJWKSet.from_dict(response.json())
    _jwks_cache[jwks_url] = (now, jwks)
    return jwks


def _find_signing_key(jwks: PyJWKSet, kid: str | None) -> PyJWK:
    if not kid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a key id (kid) header.",
        )
    for key in jwks.keys:
        if key.key_id == kid:
            return key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token signed by an unknown key.",
    )


async def verify_clerk_token(token: str) -> dict[str, Any]:
    """Verify a Clerk JWT against the cached JWKS and return its claims.

    Raises HTTPException(401) for any token/signature/expiry problem and
    HTTPException(503) if the server isn't configured with a JWKS URL.
    """
    settings = get_settings()
    if not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on the server.",
        )
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token header could not be parsed.",
        ) from exc
    jwks = await _fetch_jwks(settings.clerk_jwks_url)
    signing_key = _find_signing_key(jwks, header.get("kid"))
    algorithm = header.get("alg") or "RS256"
    try:
        # Clerk session tokens don't always populate aud; iss check is skipped
        # because the JWKS endpoint itself is the trust root.
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            options={"verify_aud": False, "verify_iss": False},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature could not be verified.",
        ) from exc
    return claims


def _extract_email(claims: dict[str, Any]) -> str:
    # Clerk JWT templates can emit the email under several keys depending on
    # how the template is configured; try the common ones in order.
    for key in ("email", "email_address", "primary_email_address"):
        value = claims.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


async def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> dict[str, Any]:
    """FastAPI dep that gates a route to allowlisted admin emails."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = await verify_clerk_token(credentials.credentials)
    settings = get_settings()
    email = _extract_email(claims).lower()
    allowed = {e.lower() for e in settings.admin_emails}
    if not email or email not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for admin access.",
        )
    return claims


AdminClaims = Annotated[dict[str, Any], Depends(require_admin)]
