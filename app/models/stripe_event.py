from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase, utcnow


class StripeEvent(TimestampedBase):
    """Idempotency log: each Stripe webhook event is recorded so we never
    double-process on retry."""

    __tablename__ = "stripe_events"

    stripe_event_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
