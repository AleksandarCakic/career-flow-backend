"""Integration tests for the public read endpoints.

Requires DATABASE_URL pointing at a Postgres instance with the latest
migration applied. CI uses a fresh `postgres:16` service.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import Coach
from app.models.package import Package, PackageTier, PricingModel
from app.models.success_story import SuccessStory


@pytest.fixture
async def seeded_coach(db_session: AsyncSession) -> Coach:
    coach = Coach(
        email="test@career-flow.com",
        name="Test Coach",
        slug="test-coach",
        title="Test Title",
        bio_short="Short bio",
        bio_long="Long bio",
        calendly_url="https://calendly.example/test",
        is_active=True,
        sort_order=10,
    )
    db_session.add(coach)
    await db_session.commit()
    await db_session.refresh(coach)
    return coach


@pytest.mark.integration
async def test_list_coaches_returns_active(client: AsyncClient, seeded_coach: Coach) -> None:
    response = await client.get("/coaches")
    assert response.status_code == 200
    payload = response.json()
    slugs = {entry["slug"] for entry in payload}
    assert seeded_coach.slug in slugs


@pytest.mark.integration
async def test_get_coach_by_slug(client: AsyncClient, seeded_coach: Coach) -> None:
    response = await client.get(f"/coaches/{seeded_coach.slug}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["slug"] == seeded_coach.slug
    assert payload["name"] == seeded_coach.name


@pytest.mark.integration
async def test_get_coach_missing_returns_404(client: AsyncClient) -> None:
    response = await client.get("/coaches/this-does-not-exist")
    assert response.status_code == 404


@pytest.mark.integration
async def test_list_packages(client: AsyncClient, db_session: AsyncSession) -> None:
    pkg = Package(
        slug="test-pkg",
        name="Test Package",
        tier=PackageTier.NAVIGATOR,
        pricing_model=PricingModel.SUBSCRIPTION_MONTHLY,
        amount_cents=100000,
        description="A test package",
        features=["Feature one", "Feature two"],
        is_active=True,
    )
    db_session.add(pkg)
    await db_session.commit()

    response = await client.get("/packages")
    assert response.status_code == 200
    slugs = {entry["slug"] for entry in response.json()}
    assert "test-pkg" in slugs


@pytest.mark.integration
async def test_list_success_stories_omits_unpublished(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Seed everything inline (no separate seeded_coach fixture) and commit
    # once before any HTTP traffic — earlier versions of this test combined a
    # fixture-managed session with a follow-up HTTP request, which triggered
    # asyncpg "another operation in progress". Single-commit + explicit close
    # below sidesteps that.
    coach = Coach(
        email="story-coach@career-flow.com",
        name="Story Coach",
        slug="story-coach",
        title="Test Title",
        bio_short="Short bio",
        bio_long="Long bio",
        calendly_url="https://calendly.example/story",
        is_active=True,
        sort_order=42,
    )
    db_session.add(coach)
    await db_session.flush()  # populate coach.id without releasing the txn

    db_session.add_all(
        [
            SuccessStory(
                slug="story-published",
                client_name="Pat",
                client_role_before="X",
                client_role_after="Y",
                client_company_after="Acme",
                story_short="Worked out great.",
                coach_id=coach.id,
                is_featured=True,
                sort_order=0,
                published_at=datetime.now(UTC),
            ),
            SuccessStory(
                slug="story-draft",
                client_name="Drew",
                client_role_before="A",
                client_role_after="B",
                client_company_after="Beta",
                story_short="In progress.",
                coach_id=coach.id,
                is_featured=False,
                sort_order=1,
                published_at=None,
            ),
        ]
    )
    await db_session.commit()
    # Drop any in-flight asyncpg cursor state from the seed before issuing
    # an HTTP request that opens its own session on the same engine.
    await db_session.close()

    response = await client.get("/success-stories")
    assert response.status_code == 200
    slugs = {entry["slug"] for entry in response.json()}
    assert "story-published" in slugs
    assert "story-draft" not in slugs
    published_entry = next(e for e in response.json() if e["slug"] == "story-published")
    assert published_entry["coach_slug"] == coach.slug
