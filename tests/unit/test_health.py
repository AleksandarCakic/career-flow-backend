from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import AsyncClient

from app.api.deps import get_db_session
from app.main import app


@pytest.mark.unit
async def test_healthz_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class _BrokenSession:
    """Minimal stand-in for AsyncSession whose execute() always raises."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("simulated db outage")


@pytest.mark.unit
async def test_readyz_returns_503_when_db_unreachable(client: AsyncClient) -> None:
    """Override the DB dependency to simulate a Postgres outage."""

    async def _broken_dep() -> AsyncIterator[Any]:
        yield _BrokenSession()

    previous = app.dependency_overrides.get(get_db_session)
    app.dependency_overrides[get_db_session] = _broken_dep
    try:
        response = await client.get("/readyz")
        assert response.status_code == 503
        assert "not reachable" in response.json()["detail"].lower()
    finally:
        if previous is None:
            del app.dependency_overrides[get_db_session]
        else:
            app.dependency_overrides[get_db_session] = previous
