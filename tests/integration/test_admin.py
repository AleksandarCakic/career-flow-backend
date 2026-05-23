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
from app.models import Coach, Lead, LeadStatus, QuizResponse, SuccessStory, WaitlistEntry

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
    response = await client.get("/admin/leads", headers={"Authorization": f"Bearer {admin_token}"})
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
    await db_session.close()  # release the asyncpg connection before HTTP
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


# --- Write actions (Week 6) ---------------------------------------------------


@pytest.mark.integration
async def test_admin_coaches_list_includes_inactive(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_coach: Coach,
) -> None:
    inactive = Coach(
        email="inactive@career-flow.com",
        name="Inactive Coach",
        slug="inactive-coach",
        title="Inactive",
        bio_short="",
        bio_long="",
        calendly_url="https://calendly.example/inactive",
        is_active=False,
        sort_order=999,
    )
    db_session.add(inactive)
    await db_session.commit()
    await db_session.close()
    response = await client.get(
        "/admin/coaches", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    items = response.json()
    slugs = {item["slug"] for item in items}
    assert seeded_coach.slug in slugs
    assert "inactive-coach" in slugs
    inactive_row = next(item for item in items if item["slug"] == "inactive-coach")
    assert inactive_row["is_active"] is False


@pytest.mark.integration
async def test_admin_coaches_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/admin/coaches")
    assert response.status_code == 401


@pytest.mark.integration
async def test_update_lead_changes_status(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    lead = seeded_leads[0]
    response = await client.patch(
        f"/admin/leads/{lead.id}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "contacted"


@pytest.mark.integration
async def test_update_lead_assigns_coach(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
    seeded_coach: Coach,
) -> None:
    lead = seeded_leads[1]  # unassigned coach in seed
    assert lead.assigned_coach_id is None
    response = await client.patch(
        f"/admin/leads/{lead.id}",
        json={"assigned_coach_id": str(seeded_coach.id)},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["assigned_coach_id"] == str(seeded_coach.id)
    assert payload["assigned_coach_slug"] == seeded_coach.slug


@pytest.mark.integration
async def test_update_lead_unassigns_coach(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    lead = seeded_leads[0]  # has a coach assigned in seed
    assert lead.assigned_coach_id is not None
    response = await client.patch(
        f"/admin/leads/{lead.id}",
        json={"assigned_coach_id": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["assigned_coach_id"] is None
    assert response.json()["assigned_coach_slug"] is None


@pytest.mark.integration
async def test_update_lead_404_when_missing(
    client: AsyncClient, jwks_mock: respx.Router, admin_token: str
) -> None:
    import uuid

    response = await client.patch(
        f"/admin/leads/{uuid.uuid4()}",
        json={"status": "contacted"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_update_lead_422_on_unknown_coach(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    import uuid

    response = await client.patch(
        f"/admin/leads/{seeded_leads[0].id}",
        json={"assigned_coach_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_update_lead_requires_admin(client: AsyncClient, seeded_leads: list[Lead]) -> None:
    response = await client.patch(
        f"/admin/leads/{seeded_leads[0].id}",
        json={"status": "contacted"},
    )
    assert response.status_code == 401


@pytest.mark.integration
async def test_create_success_story(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_coach: Coach,
) -> None:
    response = await client.post(
        "/admin/success-stories",
        json={
            "slug": "alex-promoted",
            "client_name": "Alex Example",
            "client_role_before": "Engineer",
            "client_role_after": "Engineering Manager",
            "story_short": "Got promoted",
            "coach_id": str(seeded_coach.id),
            "is_featured": True,
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["slug"] == "alex-promoted"
    assert payload["coach_slug"] == seeded_coach.slug
    assert payload["is_featured"] is True


@pytest.mark.integration
async def test_create_success_story_rejects_duplicate_slug(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    existing = SuccessStory(
        slug="dup-slug",
        client_name="Existing",
        story_short="Hi",
    )
    db_session.add(existing)
    await db_session.commit()
    response = await client.post(
        "/admin/success-stories",
        json={"slug": "dup-slug", "client_name": "New", "story_short": "Hi"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.integration
async def test_update_success_story_publishes_and_unpublishes(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    story = SuccessStory(slug="toggle-me", client_name="Toggle", story_short="x")
    db_session.add(story)
    await db_session.commit()
    await db_session.refresh(story)

    # Publish
    response = await client.patch(
        f"/admin/success-stories/{story.id}",
        json={"published_at": "2026-05-23T00:00:00Z"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["published_at"] is not None

    # Unpublish
    response = await client.patch(
        f"/admin/success-stories/{story.id}",
        json={"published_at": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["published_at"] is None


@pytest.mark.integration
async def test_delete_success_story_is_soft(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    story = SuccessStory(slug="trash-me", client_name="Trash", story_short="x")
    db_session.add(story)
    await db_session.commit()
    await db_session.refresh(story)
    story_id = story.id

    response = await client.delete(
        f"/admin/success-stories/{story_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 204

    # Deleted row should no longer appear in the admin list.
    list_response = await client.get(
        "/admin/success-stories",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    slugs = {item["slug"] for item in list_response.json()["items"]}
    assert "trash-me" not in slugs

    # Second delete returns 404.
    response = await client.delete(
        f"/admin/success-stories/{story_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_success_story_write_endpoints_require_admin(
    client: AsyncClient,
) -> None:
    assert (await client.post("/admin/success-stories", json={})).status_code == 401
    import uuid

    sid = uuid.uuid4()
    assert (await client.patch(f"/admin/success-stories/{sid}", json={})).status_code == 401
    assert (await client.delete(f"/admin/success-stories/{sid}")).status_code == 401


# --- Week 7: notes + filtering/search ----------------------------------------


@pytest.mark.integration
async def test_update_lead_persists_notes(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    lead = seeded_leads[0]
    response = await client.patch(
        f"/admin/leads/{lead.id}",
        json={"notes": "Called 5/22 — qualified, sending Stripe link"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Called 5/22 — qualified, sending Stripe link"


@pytest.mark.integration
async def test_update_lead_can_clear_notes(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_coach: Coach,
) -> None:
    lead = Lead(
        name="With Notes",
        email="notes@example.com",
        notes="initial",
        status=LeadStatus.NEW,
    )
    db_session.add(lead)
    await db_session.commit()
    await db_session.refresh(lead)
    lead_id = lead.id
    await db_session.close()

    response = await client.patch(
        f"/admin/leads/{lead_id}",
        json={"notes": None},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["notes"] is None


@pytest.mark.integration
async def test_list_leads_filters_by_status(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_leads: list[Lead],
) -> None:
    seeded_leads[0].status = LeadStatus.QUALIFIED
    await db_session.commit()
    await db_session.close()

    response = await client.get(
        "/admin/leads?status=qualified",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    payload = response.json()
    statuses = {item["status"] for item in payload["items"]}
    assert statuses == {"qualified"}
    assert payload["total"] >= 1


@pytest.mark.integration
async def test_list_leads_search_matches_name_or_email(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    db_session.add_all(
        [
            Lead(name="Searchable Person", email="findme@example.com", status=LeadStatus.NEW),
            Lead(name="Other", email="unrelated@example.com", status=LeadStatus.NEW),
        ]
    )
    await db_session.commit()

    by_name = await client.get(
        "/admin/leads?search=searchable",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    by_email = await client.get(
        "/admin/leads?search=findme",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    for response in (by_name, by_email):
        assert response.status_code == 200
        items = response.json()["items"]
        assert all(
            "searchable" in item["name"].lower() or "findme" in item["email"] for item in items
        )
        assert any(item["email"] == "findme@example.com" for item in items)


@pytest.mark.integration
async def test_list_leads_filter_total_excludes_filtered_out_rows(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_leads: list[Lead],
) -> None:
    # Make exactly one lead `paid`; total must be 1 for that filter.
    seeded_leads[0].status = LeadStatus.PAID
    await db_session.commit()
    await db_session.close()

    response = await client.get(
        "/admin/leads?status=paid",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


# --- Week 8: CSV exports ------------------------------------------------------


@pytest.mark.integration
async def test_export_leads_csv_requires_admin(client: AsyncClient) -> None:
    response = await client.get("/admin/leads/export.csv")
    assert response.status_code == 401


@pytest.mark.integration
async def test_export_leads_csv_returns_csv(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    seeded_leads: list[Lead],
) -> None:
    response = await client.get(
        "/admin/leads/export.csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]
    body = response.text
    lines = body.splitlines()
    # Header + 3 seeded leads
    assert lines[0].startswith("id,created_at,updated_at,name,email")
    assert len(lines) >= 4
    # All seeded emails appear somewhere in the body
    assert "lead0@example.com" in body
    assert "lead2@example.com" in body


@pytest.mark.integration
async def test_export_leads_csv_honors_status_filter(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
    seeded_leads: list[Lead],
) -> None:
    seeded_leads[0].status = LeadStatus.PAID
    await db_session.commit()
    await db_session.close()

    response = await client.get(
        "/admin/leads/export.csv?status=paid",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    lines = response.text.splitlines()
    assert len(lines) == 2  # header + 1 paid row


@pytest.mark.integration
async def test_export_waitlist_csv_returns_csv(
    client: AsyncClient,
    jwks_mock: respx.Router,
    admin_token: str,
    db_session: AsyncSession,
) -> None:
    db_session.add(
        WaitlistEntry(
            email="csv-waitlist@example.com",
            current_role="Engineer",
            years_of_experience="5-10",
            biggest_challenge="Need direction",
            workshop_interests=["resume", "interview"],
        )
    )
    await db_session.commit()

    response = await client.get(
        "/admin/waitlist/export.csv",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    body = response.text
    assert "csv-waitlist@example.com" in body
    # workshop_interests is a list — should be flattened with `, `
    assert "resume, interview" in body
