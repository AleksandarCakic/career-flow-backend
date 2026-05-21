from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class QuizResponse(TimestampedBase):
    __tablename__ = "quiz_responses"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    answers: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    matched_coach_id: Mapped[UUID | None] = mapped_column(ForeignKey("coaches.id"))
    posthog_distinct_id: Mapped[str | None] = mapped_column(String(120))
