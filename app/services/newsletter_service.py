"""Newsletter subscription business logic.

Re-subscribe creates a new row rather than mutating the old one, so we
keep a full audit trail. Confirmation tokens are URL-safe 32-byte random
strings; if a user re-submits the form before confirming, we issue a
fresh row + token rather than reusing the old one (so a leaked stale
token can't confirm a fresh subscribe).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.newsletter_subscription import NewsletterSubscription


class NewsletterService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_pending(
        self,
        email: str,
        source: str | None,
        posthog_distinct_id: str | None,
    ) -> NewsletterSubscription:
        row = NewsletterSubscription(
            email=email.lower(),
            confirmation_token=secrets.token_urlsafe(32),
            source=source,
            posthog_distinct_id=posthog_distinct_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def find_by_token(self, token: str) -> NewsletterSubscription | None:
        stmt = select(NewsletterSubscription).where(
            NewsletterSubscription.confirmation_token == token
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def confirm(self, row: NewsletterSubscription) -> bool:
        """Returns True if newly confirmed; False if already confirmed."""
        if row.confirmed_at is not None:
            return False
        row.confirmed_at = datetime.now(UTC)
        await self.db.commit()
        return True

    async def unsubscribe(self, row: NewsletterSubscription) -> bool:
        """Returns True if newly unsubscribed; False if already unsubscribed."""
        if row.unsubscribed_at is not None:
            return False
        row.unsubscribed_at = datetime.now(UTC)
        await self.db.commit()
        return True
