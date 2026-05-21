"""Resend transactional email wrapper.

Sends pre-rendered HTML via the Resend REST API. Calls are async and use
a 10-second timeout. No-ops when RESEND_API_KEY is unset (dev / preview).
"""

import httpx
import structlog

from app.core.config import get_settings

log = structlog.get_logger(__name__)

RESEND_API_BASE = "https://api.resend.com"


class EmailService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._settings = get_settings()
        self._client = client

    async def send(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        from_address: str | None = None,
    ) -> bool:
        """Send a single transactional email. Returns True on success, False
        when skipped (no API key) or on failure."""
        api_key = self._settings.resend_api_key
        if not api_key:
            log.debug("email.skipped", reason="resend_api_key_unset", to=to)
            return False

        sender = from_address or self._settings.resend_from_noreply
        payload = {
            "from": sender,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        try:
            if self._client is None:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{RESEND_API_BASE}/emails", json=payload, headers=headers
                    )
            else:
                response = await self._client.post(
                    f"{RESEND_API_BASE}/emails", json=payload, headers=headers
                )
            response.raise_for_status()
            log.info("email.sent", to=to, subject=subject)
            return True
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            log.warning("email.send_failed", to=to, subject=subject, error=str(exc))
            return False
