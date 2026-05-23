from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class NewsletterSubscription(TimestampedBase):
    """A single subscribe request for the Career Flow mailing list.

    Multiple rows per email are allowed — re-subscribing after an unsubscribe
    creates a new row rather than mutating the old one, so we keep a full
    audit trail. List-management queries should filter to the most recent
    row per email with `unsubscribed_at IS NULL AND confirmed_at IS NOT NULL`.
    """

    __tablename__ = "newsletter_subscriptions"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    confirmation_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posthog_distinct_id: Mapped[str | None] = mapped_column(String(120))
    source: Mapped[str | None] = mapped_column(String(80))
