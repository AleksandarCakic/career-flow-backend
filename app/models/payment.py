import enum
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(TimestampedBase):
    __tablename__ = "payments"

    stripe_payment_intent_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(120))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(120))
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(120))
    coach_id: Mapped[UUID | None] = mapped_column(ForeignKey("coaches.id"))
    package_id: Mapped[UUID | None] = mapped_column(ForeignKey("packages.id"))
    lead_id: Mapped[UUID | None] = mapped_column(ForeignKey("leads.id"))
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    raw_event: Mapped[dict[str, Any] | None] = mapped_column(JSON)
