"""PostHog server-side event capture.

Hand-rolled httpx wrapper around PostHog's `/capture/` endpoint — avoids
adding the official SDK dependency for now since we only need fire-and-
forget event sends. Matches the no-op-when-unconfigured pattern used by
the other side-effect services (`slack_service.py`, `email_service.py`).
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import get_settings

log = structlog.get_logger(__name__)


class PostHogService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._api_key = settings.posthog_api_key
        # PostHog hosts are bare domains (e.g. "https://eu.posthog.com");
        # the capture endpoint is appended.
        self._host = settings.posthog_host.rstrip("/")
        self._client = client

    async def capture(
        self,
        distinct_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
    ) -> bool:
        """Send a `capture` event. Returns True if posted, False on no-op/failure.

        No-ops + logs once when `POSTHOG_API_KEY` is unset; logs a warning and
        swallows on HTTP/network errors so the calling request still succeeds.
        """
        if not self._api_key:
            log.debug("posthog.skipped", reason="api_key_unset", event_name=event)
            return False
        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "event": event,
            "distinct_id": distinct_id,
        }
        if properties:
            payload["properties"] = properties
        url = f"{self._host}/capture/"
        try:
            async with (
                httpx.AsyncClient(timeout=5.0)
                if self._client is None
                else _no_close(self._client) as client
            ):
                response = await client.post(url, json=payload)
                response.raise_for_status()
            log.info("posthog.captured", event_name=event, distinct_id=distinct_id)
            return True
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            log.warning("posthog.capture_failed", event_name=event, error=str(exc))
            return False


class _no_close:
    """Context manager that yields a borrowed httpx client without closing it
    (used when callers pass their own client in)."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *args: object) -> None:
        return None
