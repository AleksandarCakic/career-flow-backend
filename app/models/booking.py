import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class BookingStatus(enum.StrEnum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELED = "canceled"
    NO_SHOW = "no_show"


class Booking(TimestampedBase):
    __tablename__ = "bookings"

    calendly_event_uri: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    coach_id: Mapped[UUID | None] = mapped_column(ForeignKey("coaches.id"))
    invitee_email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    invitee_name: Mapped[str | None] = mapped_column(String(200))
    event_type: Mapped[str | None] = mapped_column(String(200))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status"),
        default=BookingStatus.SCHEDULED,
        nullable=False,
    )
    lead_id: Mapped[UUID | None] = mapped_column(ForeignKey("leads.id"))
