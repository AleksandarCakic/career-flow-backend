"""Slack incoming-webhook dispatcher.

Posts JSON payloads (Slack Block Kit) to channel-specific webhook URLs.
No-ops when a webhook URL is unset — important so dev / preview environments
don't error if credentials aren't configured yet.
"""

from typing import Any

import httpx
import structlog

from app.core.config import get_settings

log = structlog.get_logger(__name__)


class SlackChannel:
    LEADS = "leads"
    BOOKINGS = "bookings"
    PAYMENTS = "payments"
    ALERTS = "alerts"


class SlackService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._urls: dict[str, str] = {
            SlackChannel.LEADS: settings.slack_webhook_leads,
            SlackChannel.BOOKINGS: settings.slack_webhook_bookings,
            SlackChannel.PAYMENTS: settings.slack_webhook_payments,
            SlackChannel.ALERTS: settings.slack_webhook_alerts,
        }
        self._client = client

    async def _post(self, url: str, payload: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=5.0) if self._client is None else _no_close(
            self._client
        ) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()

    async def post(
        self,
        channel: str,
        text: str,
        blocks: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Post a message to a named channel webhook. Returns True if posted.

        Returns False (no-op) when the channel's webhook URL is unset.
        """
        url = self._urls.get(channel, "")
        if not url:
            log.debug("slack.skipped", channel=channel, reason="webhook_unset")
            return False
        payload: dict[str, Any] = {"text": text}
        if blocks:
            payload["blocks"] = blocks
        try:
            await self._post(url, payload)
            log.info("slack.posted", channel=channel)
            return True
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            log.warning("slack.post_failed", channel=channel, error=str(exc))
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
