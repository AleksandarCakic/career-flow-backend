"""Email-gated PDF download flow.

`request_download` creates a ResourceDownload row with a one-time token and
returns it for emailing. `validate_token` confirms the token is active
(not expired, not already redeemed) and marks it redeemed on success.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resource_download import ResourceDownload

TOKEN_BYTES = 32  # 256 bits of entropy -> 43-char URL-safe string
TOKEN_TTL_DAYS = 7

# Resource catalog. Each entry's `file_path` is the on-disk location relative
# to the backend repo (PDF files are copied in by hand for now). Update when
# new resources land.
RESOURCE_CATALOG: dict[str, dict[str, str]] = {
    "resume-guide": {
        "title": "The Career Flow Resume Guide",
        "file_path": "app/resources_static/resume-guide.pdf",
    },
    "linkedin-guide": {
        "title": "The Career Flow LinkedIn Guide",
        "file_path": "app/resources_static/linkedin-guide.pdf",
    },
    "interview-prep": {
        "title": "Interview Prep Playbook",
        "file_path": "app/resources_static/interview-prep.pdf",
    },
}


class PdfService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    @staticmethod
    def known_resource(slug: str) -> bool:
        return slug in RESOURCE_CATALOG

    @staticmethod
    def resource_title(slug: str) -> str:
        entry = RESOURCE_CATALOG.get(slug, {})
        return entry.get("title", slug)

    @staticmethod
    def resource_path(slug: str) -> str | None:
        entry = RESOURCE_CATALOG.get(slug, {})
        return entry.get("file_path")

    async def request_download(
        self,
        *,
        email: str,
        resource_slug: str,
        posthog_distinct_id: str | None = None,
    ) -> ResourceDownload:
        token = secrets.token_urlsafe(TOKEN_BYTES)
        expires = datetime.now(UTC) + timedelta(days=TOKEN_TTL_DAYS)
        download = ResourceDownload(
            email=email,
            resource_slug=resource_slug,
            download_token=token,
            expires_at=expires,
            posthog_distinct_id=posthog_distinct_id,
        )
        self.db.add(download)
        await self.db.commit()
        await self.db.refresh(download)
        return download

    async def validate_token(self, token: str) -> ResourceDownload | None:
        stmt = select(ResourceDownload).where(ResourceDownload.download_token == token)
        result = await self.db.execute(stmt)
        download = result.scalar_one_or_none()
        if not download:
            return None
        if download.downloaded_at is not None:
            return None
        if download.expires_at < datetime.now(UTC):
            return None
        return download

    async def mark_downloaded(self, download: ResourceDownload) -> None:
        download.downloaded_at = datetime.now(UTC)
        await self.db.commit()
