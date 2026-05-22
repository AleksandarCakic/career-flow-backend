"""Integration tests for /admin/* endpoints.

Verifies that every admin list endpoint:
- returns 401 when no bearer token is supplied,
- returns 403 when the token's email isn't in the admin allowlist,
- returns 200 + the expected paginated envelope when a valid admin token is
  supplied, with rows ordered newest-first and `limit`/`offset` honored.

Tokens are signed locally with a test RSA key; Clerk's JWKS endpoint is
mocked via respx so verification runs end-to-end without network access.
"""

from __future__ import annotations

import base64
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
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import security
from app.core.config import get_settings
from app.models import Coach, Lead, LeadStatus, QuizResponse, WaitlistEntry

JWKS_URL = "https://test.clerk.example.com/.well-known/jwks.json"
TEST_KID = "test-kid-admin"
ADMIN_EMAIL = "alex@career-flow.com"
OTHER_EMAIL = "stranger@example.com"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@pytest.fixture(scope="module")
def rsa_keypair() -> rsa.RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks_doc(rsa_keypair: rsa.RSAPrivateKey) -> dict[str, Any]:
    public_numbers = rsa_keypair.public_key().public_numbers()
    n = public_numbers.n.to_bytes((public_numbers.n.bit_length() + 7) // 8, "big")
    e = public_numbers.e.to_bytes((public_numbers.e.bit_length() + 7) // 8, "big")
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": TEST_KID,
                "n": _b64url(n),
                "e": _b64url(e),
            }
        ]
    }


def _sign(key: rsa.RSAPrivateKey, claims: dict[str, Any]) -> str:
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": TEST_KID})


@pytest.fixture(autouse=True)
def configure_clerk(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
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


@pytest.fixture
def admin_token(rsa_keypair: rsa.RSAPrivateKey) -> str:
    return _sign(rsa_keypair, {"email": ADMIN_EMAIL, "exp": int(time.time()) + 600})


@pytest.fixture
def non_admin_token(rsa_keypair: rsa.RSAPrivateKey) -> str:
    return _sign(rsa_keypair, {"email": OTHER_EMAIL, "exp": int(time.time()) + 600})


@pytest.fixture
async def seeded_coach(db_session: AsyncSession) -> Coach:
    coach = Coach(
        email="admin-test@career-flow.com",
        name="Admin Test Coach",
        slug="admin-test-coach",
        title="Title",
        bio_short="Short",
        bio_long="Long",
        calendly_url="https://calendly.example/admin-test",
        is_active=True,
        sort_order=99,
    )
    db_session.add(coach)
    await db_session.commit()
    await db_session.refresh(coach)
    return coach


@pytest.fixture
async def seeded_leads(db_session: AsyncSession, seeded_coach: Coach) -> list[Lead]:
    leads = [
        Lead(
            name=f"Lead {i}",
            email=f"lead{i}@example.com",
            subject="Hello",
            message=f"Message {i}",
            assigned_coach_id=seeded_coach.id if i % 2 == 0 else None,
            status=LeadStatus.NEW,
        )
        for i in range(3)
    ]
    for lead in leads:
        db_session.add(lead)
    await db_session.commit()
    for lead in leads:
        await db_session.refresh(lead)
    return leads


ENDPOINTS = [
    "/admin/leads",
    "/admin/waitlist",
    "/admin/quiz-responses",
    "/admin/bookings",
    "/admin/payments",
    "/admin/success-stories",
]


@pytest.mark.integration
@pytest.mark.parametrize("path", ENDPOINTS)
async def test_admin_endpoint_requires_token(client: AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.parametrize("path", ENDPOINTS)
async def test_admin_endpoint_rejects_non_admin_token(
    client: AsyncClient, jwks_mock: respx.Router, non_admin_token: str, path: str
) -> None:
    response = await client.get(path, headers={"Authorization": f"Bearer {non_admin_token}"})
    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize("path", ENDPOINTS)
async def test_admin_endpoint_returns_envelope_for_admin(
    client: AsyncClient, jwks_mock: respx.Router, admin_token: str, path: str
) -> None:
    response = await client.get(path, headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"items", "total", "limit", "offset"}
    assert isinstance(payload["items"], list)
    assert payload["limit"] == 50
    assert payload["offset"] == 0


@pytest.mark.integration
async def test_admin_leads_orders_newest_first_and_includes_coach_slug(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
    seeded_coach: Coach,
) -> None:
    response = await client.get(
        "/admin/leads", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 3
    emails = [item["email"] for item in payload["items"][:3]]
    # Inserted in order Lead 0, 1, 2 — newest first means Lead 2 leads.
    assert emails[0] == "lead2@example.com"
    # The even-indexed lead (0 and 2) was assigned to seeded_coach.
    assigned = next(item for item in payload["items"] if item["email"] == "lead2@example.com")
    assert assigned["assigned_coach_slug"] == seeded_coach.slug


@pytest.mark.integration
async def test_admin_leads_honors_pagination(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    response = await client.get(
        "/admin/leads?limit=1&offset=1",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert len(payload["items"]) == 1


@pytest.mark.integration
async def test_admin_waitlist_returns_seeded_row(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    entry = WaitlistEntry(
        email="waitlist@example.com",
        current_role="Engineer",
        years_of_experience="3-5",
        biggest_challenge="Direction",
        workshop_interests=["resume"],
    )
    db_session.add(entry)
    await db_session.commit()
    response = await client.get(
        "/admin/waitlist", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    payload = response.json()
    emails = {item["email"] for item in payload["items"]}
    assert "waitlist@example.com" in emails


@pytest.mark.integration
async def test_admin_quiz_responses_join_coach_slug(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_coach: Coach,
) -> None:
    quiz = QuizResponse(
        email="quiz@example.com",
        answers={"q1": "a"},
        matched_coach_id=seeded_coach.id,
    )
    db_session.add(quiz)
    await db_session.commit()
    response = await client.get(
        "/admin/quiz-responses", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    payload = response.json()
    matched = next(item for item in payload["items"] if item["email"] == "quiz@example.com")
    assert matched["matched_coach_slug"] == seeded_coach.slug


@pytest.mark.integration
async def test_admin_endpoint_rejects_bad_limit(
    client: AsyncClient, jwks_mock: respx.Router, admin_token: str
) -> None:
    response = await client.get(
        "/admin/leads?limit=9999",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
