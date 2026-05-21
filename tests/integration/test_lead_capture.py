"""Integration tests for the lead-capture endpoints: /contact, /waitlist, /quiz."""

from typing import Any

import pytest
import respx
from httpx import AsyncClient, Response

from app.services.email_service import RESEND_API_BASE


@pytest.fixture
def email_mock() -> respx.Router:
    """Mock the Resend API so tests don't make real network calls."""
    with respx.mock(base_url=RESEND_API_BASE, assert_all_called=False) as mock:
        mock.post("/emails").mock(return_value=Response(200, json={"id": "test-msg-id"}))
        yield mock


@pytest.fixture
def slack_mock() -> respx.Router:
    with respx.mock(assert_all_called=False) as mock:
        mock.post(url__startswith="https://hooks.slack.com").mock(return_value=Response(200))
        yield mock


@pytest.mark.integration
async def test_contact_submission(
    client: AsyncClient, email_mock: respx.Router, slack_mock: respx.Router
) -> None:
    payload: dict[str, Any] = {
        "name": "Pat Patterson",
        "email": "pat@example.com",
        "subject": "Coaching enquiry",
        "message": "I'd like to learn more about your 1-on-1 coaching.",
        "source_page": "/contact",
    }
    response = await client.post("/contact", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert "id" in body


@pytest.mark.integration
async def test_contact_rejects_short_message(client: AsyncClient) -> None:
    response = await client.post(
        "/contact",
        json={
            "name": "Pat",
            "email": "pat@example.com",
            "subject": "Question",
            "message": "short",
        },
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_contact_rejects_bad_email(client: AsyncClient) -> None:
    response = await client.post(
        "/contact",
        json={
            "name": "Pat",
            "email": "not-an-email",
            "subject": "Question",
            "message": "A long enough message here.",
        },
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_waitlist_submission(
    client: AsyncClient, email_mock: respx.Router, slack_mock: respx.Router
) -> None:
    response = await client.post(
        "/waitlist",
        json={
            "email": "drew@example.com",
            "current_role": "Engineering Manager",
            "years_of_experience": "11-15 years",
            "biggest_challenge": "Stepping into a Director role at a new company.",
            "linkedin_profile": "https://linkedin.com/in/drew",
            "coach_preference": "atiyeh",
            "workshop_interests": ["Leadership development", "Personal brand"],
        },
    )
    assert response.status_code == 201, response.text
    assert "id" in response.json()


@pytest.mark.integration
async def test_quiz_submission(
    client: AsyncClient, slack_mock: respx.Router
) -> None:
    response = await client.post(
        "/quiz",
        json={
            "email": "quiz@example.com",
            "answers": {"career-stage": "growing-tech-role", "timeline": "next-3-months"},
            "matched_coach_slug": "alex",
        },
    )
    assert response.status_code == 201, response.text
    assert "id" in response.json()
