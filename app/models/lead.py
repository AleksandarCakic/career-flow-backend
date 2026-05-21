import enum
from uuid import UUID

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class LeadStatus(enum.StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    BOOKED = "booked"
    PAID = "paid"
    LOST = "lost"


class Lead(TimestampedBase):
    __tablename__ = "leads"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    subject: Mapped[str | None] = mapped_column(String(300))
    message: Mapped[str | None] = mapped_column(String)
    source_page: Mapped[str | None] = mapped_column(String(200))
    posthog_distinct_id: Mapped[str | None] = mapped_column(String(120))
    assigned_coach_id: Mapped[UUID | None] = mapped_column(ForeignKey("coaches.id"))
    status: Mapped[LeadStatus] = mapped_column(
        SAEnum(LeadStatus, name="lead_status"),
        default=LeadStatus.NEW,
        nullable=False,
    )
