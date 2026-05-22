"""Unit tests for Clerk JWT verification and admin allowlist enforcement.

A test RSA keypair is generated per test session; tokens are signed locally
with the private key and the matching public key is exposed via a respx-
mocked JWKS endpoint so verification runs end-to-end without touching Clerk.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from typing import Any

import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import security
from app.core.config import get_settings

JWKS_URL = "https://test.clerk.example.com/.well-known/jwks.json"
TEST_KID = "test-kid-001"
ADMIN_EMAIL = "alex@career-flow.com"
OTHER_EMAIL = "stranger@example.com"


@pytest.fixture(scope="module")
def rsa_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks_doc(rsa_keypair: rsa.RSAPrivateKey) -> dict[str, Any]:
    public_numbers = rsa_keypair.public_key().public_numbers()
    n = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    e = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
    import base64

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": TEST_KID,
                "n": b64url(n),
                "e": b64url(e),
            }
        ]
    }


def _sign(key: rsa.RSAPrivateKey, claims: dict[str, Any], kid: str = TEST_KID) -> str:
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture(autouse=True)
def configure_clerk_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    get_settings.cache_clear()
    monkeypatch.setenv("CLERK_JWKS_URL", JWKS_URL)
    monkeypatch.setenv("ADMIN_EMAILS", json.dumps([ADMIN_EMAIL]))
    security.clear_jwks_cache()
    yield
    get_settings.cache_clear()
    security.clear_jwks_cache()


@pytest.fixture
def jwks_mock(jwks_doc: dict[str, Any]) -> Iterator[respx.Router]:
    with respx.mock(assert_all_called=False) as mock:
        mock.get(JWKS_URL).mock(return_value=httpx.Response(200, json=jwks_doc))
        yield mock


@pytest.mark.unit
async def test_verify_clerk_token_returns_claims_for_valid_token(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": ADMIN_EMAIL, "sub": "user_1", "exp": int(time.time()) + 600},
    )
    claims = await security.verify_clerk_token(token)
    assert claims["email"] == ADMIN_EMAIL
    assert claims["sub"] == "user_1"


@pytest.mark.unit
async def test_verify_clerk_token_rejects_expired_token(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": ADMIN_EMAIL, "sub": "user_1", "exp": int(time.time()) - 10},
    )
    with pytest.raises(HTTPException) as exc:
        await security.verify_clerk_token(token)
    assert exc.value.status_code == 401


@pytest.mark.unit
async def test_verify_clerk_token_rejects_unknown_kid(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": ADMIN_EMAIL, "exp": int(time.time()) + 600},
        kid="not-in-jwks",
    )
    with pytest.raises(HTTPException) as exc:
        await security.verify_clerk_token(token)
    assert exc.value.status_code == 401


@pytest.mark.unit
async def test_verify_clerk_token_returns_503_when_jwks_url_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CLERK_JWKS_URL", raising=False)
    get_settings.cache_clear()
    with pytest.raises(HTTPException) as exc:
        await security.verify_clerk_token("anything")
    assert exc.value.status_code == 503


@pytest.mark.unit
async def test_require_admin_accepts_allowlisted_email(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": ADMIN_EMAIL, "exp": int(time.time()) + 600},
    )
    from fastapi.security import HTTPAuthorizationCredentials

    claims = await security.require_admin(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    assert claims["email"] == ADMIN_EMAIL


@pytest.mark.unit
async def test_require_admin_rejects_non_allowlisted_email(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": OTHER_EMAIL, "exp": int(time.time()) + 600},
    )
    from fastapi.security import HTTPAuthorizationCredentials

    with pytest.raises(HTTPException) as exc:
        await security.require_admin(
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        )
    assert exc.value.status_code == 403


@pytest.mark.unit
async def test_require_admin_rejects_missing_token() -> None:
    with pytest.raises(HTTPException) as exc:
        await security.require_admin(credentials=None)
    assert exc.value.status_code == 401


@pytest.mark.unit
async def test_require_admin_is_case_insensitive_on_email(
    rsa_keypair: rsa.RSAPrivateKey, jwks_mock: respx.Router
) -> None:
    token = _sign(
        rsa_keypair,
        {"email": ADMIN_EMAIL.upper(), "exp": int(time.time()) + 600},
    )
    from fastapi.security import HTTPAuthorizationCredentials

    claims = await security.require_admin(
        credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    assert claims["email"].lower() == ADMIN_EMAIL
