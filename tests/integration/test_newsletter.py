"""Integration tests for /newsletter/* double-opt-in endpoints."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.newsletter_subscription import NewsletterSubscription

RESEND_API_BASE = "https://api.resend.com"


@pytest.fixture
def email_mock() -> respx.Router:  # type: ignore[no-untyped-def]
    with respx.mock(base_url=RESEND_API_BASE, assert_all_called=False) as mock:
        mock.post("/emails").respond(200, json={"id": "test-email-id"})
        yield mock


@pytest.mark.integration
async def test_subscribe_creates_pending_row_and_sends_email(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    response = await client.post(
        "/newsletter/subscribe",
        json={"email": "subscriber@example.com", "source": "footer"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending_confirmation"

    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "subscriber@example.com"
            )
        )
    ).scalar_one()
    assert row.confirmed_at is None
    assert row.unsubscribed_at is None
    assert len(row.confirmation_token) >= 32
    assert row.source == "footer"


@pytest.mark.integration
async def test_subscribe_lowercases_email(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    response = await client.post("/newsletter/subscribe", json={"email": "MixedCase@example.com"})
    assert response.status_code == 201

    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "mixedcase@example.com"
            )
        )
    ).scalar_one()
    assert row.email == "mixedcase@example.com"


@pytest.mark.integration
async def test_subscribe_invalid_email_returns_422(
    client: AsyncClient,
) -> None:
    response = await client.post("/newsletter/subscribe", json={"email": "not-an-email"})
    assert response.status_code == 422


@pytest.mark.integration
async def test_confirm_marks_confirmed_at(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    await client.post("/newsletter/subscribe", json={"email": "confirm@example.com"})
    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "confirm@example.com"
            )
        )
    ).scalar_one()
    token = row.confirmation_token

    response = await client.get(f"/newsletter/confirm?token={token}")
    assert response.status_code == 200
    assert response.json() == {"status": "confirmed", "email": "confirm@example.com"}

    await db_session.refresh(row)
    assert row.confirmed_at is not None


@pytest.mark.integration
async def test_confirm_second_call_is_idempotent(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    await client.post("/newsletter/subscribe", json={"email": "twice@example.com"})
    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "twice@example.com"
            )
        )
    ).scalar_one()
    token = row.confirmation_token

    first = await client.get(f"/newsletter/confirm?token={token}")
    second = await client.get(f"/newsletter/confirm?token={token}")
    assert first.json()["status"] == "confirmed"
    assert second.json()["status"] == "already_confirmed"


@pytest.mark.integration
async def test_confirm_unknown_token_returns_404(
    client: AsyncClient,
) -> None:
    response = await client.get("/newsletter/confirm?token=this-is-not-a-real-token")
    assert response.status_code == 404


@pytest.mark.integration
async def test_unsubscribe_marks_unsubscribed_at(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    await client.post("/newsletter/subscribe", json={"email": "leaving@example.com"})
    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "leaving@example.com"
            )
        )
    ).scalar_one()
    token = row.confirmation_token

    response = await client.get(f"/newsletter/unsubscribe?token={token}")
    assert response.status_code == 200
    assert response.json() == {"status": "unsubscribed", "email": "leaving@example.com"}

    await db_session.refresh(row)
    assert row.unsubscribed_at is not None


@pytest.mark.integration
async def test_unsubscribe_second_call_is_idempotent(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    await client.post("/newsletter/subscribe", json={"email": "twice-leaving@example.com"})
    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == "twice-leaving@example.com"
            )
        )
    ).scalar_one()
    token = row.confirmation_token

    first = await client.get(f"/newsletter/unsubscribe?token={token}")
    second = await client.get(f"/newsletter/unsubscribe?token={token}")
    assert first.json()["status"] == "unsubscribed"
    assert second.json()["status"] == "already_unsubscribed"


@pytest.mark.integration
async def test_confirm_returns_410_when_already_unsubscribed(
    client: AsyncClient, db_session: AsyncSession, email_mock: respx.Router
) -> None:
    await client.post("/newsletter/subscribe", json={"email": "gone@example.com"})
    row = (
        await db_session.execute(
            select(NewsletterSubscription).where(NewsletterSubscription.email == "gone@example.com")
        )
    ).scalar_one()
    token = row.confirmation_token

    await client.get(f"/newsletter/unsubscribe?token={token}")
    response = await client.get(f"/newsletter/confirm?token={token}")
    assert response.status_code == 410
