"""Integration test for /readyz against a real Postgres connection."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
async def test_readyz_returns_ready_against_real_db(client: AsyncClient) -> None:
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
