"""Unit tests for the PostHog server-side capture wrapper.

Verifies that:
- when POSTHOG_API_KEY is unset, capture is a silent no-op (returns False).
- when set, capture posts a well-formed JSON payload to {host}/capture/.
- HTTP errors are swallowed so the calling request still succeeds.
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest
import respx

from app.core.config import get_settings
from app.services.posthog_service import PostHogService


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.mark.unit
async def test_capture_noops_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTHOG_API_KEY", "")
    service = PostHogService()
    sent = await service.capture("user_1", "test.event", {"k": "v"})
    assert sent is False


@pytest.mark.unit
async def test_capture_posts_payload_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test_key")
    monkeypatch.setenv("POSTHOG_HOST", "https://eu.posthog.example.com")
    with respx.mock() as router:
        route = router.post("https://eu.posthog.example.com/capture/").mock(
            return_value=httpx.Response(200, json={"status": 1})
        )
        service = PostHogService()
        sent = await service.capture(
            "user_42",
            "lead.created",
            {"lead_id": "abc", "source": "contact"},
        )
        assert sent is True
        assert route.call_count == 1
        request = route.calls[0].request
        import json

        body = json.loads(request.content)
        assert body == {
            "api_key": "phc_test_key",
            "event": "lead.created",
            "distinct_id": "user_42",
            "properties": {"lead_id": "abc", "source": "contact"},
        }


@pytest.mark.unit
async def test_capture_swallows_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test_key")
    monkeypatch.setenv("POSTHOG_HOST", "https://eu.posthog.example.com")
    with respx.mock() as router:
        router.post("https://eu.posthog.example.com/capture/").mock(
            return_value=httpx.Response(500, text="boom")
        )
        service = PostHogService()
        sent = await service.capture("user_42", "test.event")
        assert sent is False  # raised internally, swallowed, returned False


@pytest.mark.unit
async def test_capture_trims_trailing_slash_in_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test_key")
    monkeypatch.setenv("POSTHOG_HOST", "https://eu.posthog.example.com/")
    with respx.mock() as router:
        route = router.post("https://eu.posthog.example.com/capture/").mock(
            return_value=httpx.Response(200, json={"status": 1})
        )
        service = PostHogService()
        sent = await service.capture("user_42", "test.event")
        assert sent is True
        assert route.call_count == 1


@pytest.mark.unit
async def test_capture_omits_empty_properties(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTHOG_API_KEY", "phc_test_key")
    monkeypatch.setenv("POSTHOG_HOST", "https://eu.posthog.example.com")
    with respx.mock() as router:
        route = router.post("https://eu.posthog.example.com/capture/").mock(
            return_value=httpx.Response(200, json={"status": 1})
        )
        service = PostHogService()
        await service.capture("user_42", "test.event")
        import json

        body = json.loads(route.calls[0].request.content)
        assert "properties" not in body
