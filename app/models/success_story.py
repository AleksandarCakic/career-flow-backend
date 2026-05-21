from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class SuccessStory(TimestampedBase):
    __tablename__ = "success_stories"

    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    client_role_before: Mapped[str | None] = mapped_column(String(200))
    client_role_after: Mapped[str | None] = mapped_column(String(200))
    client_company_after: Mapped[str | None] = mapped_column(String(200))
    headshot_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    story_short: Mapped[str] = mapped_column(String, nullable=False, default="")
    story_long: Mapped[str | None] = mapped_column(String)
    coach_id: Mapped[UUID | None] = mapped_column(ForeignKey("coaches.id"))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
