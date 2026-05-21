from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class WaitlistEntry(TimestampedBase):
    __tablename__ = "waitlist_entries"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    current_role: Mapped[str] = mapped_column(String(200), nullable=False)
    years_of_experience: Mapped[str] = mapped_column(String(40), nullable=False)
    biggest_challenge: Mapped[str] = mapped_column(String, nullable=False)
    linkedin_profile: Mapped[str | None] = mapped_column(String(500))
    coach_preference: Mapped[str | None] = mapped_column(String(40))
    workshop_interests: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    posthog_distinct_id: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="new", nullable=False)
