from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    message: str = Field(min_length=10, max_length=5000)
    source_page: str | None = Field(default=None, max_length=200)
    posthog_distinct_id: str | None = Field(default=None, max_length=120)


class WaitlistCreate(BaseModel):
    email: EmailStr
    current_role: str = Field(min_length=1, max_length=200)
    years_of_experience: str = Field(min_length=1, max_length=40)
    biggest_challenge: str = Field(min_length=10, max_length=2000)
    linkedin_profile: str | None = Field(default=None, max_length=500)
    coach_preference: str | None = Field(default=None, max_length=40)
    workshop_interests: list[str] = Field(default_factory=list)
    posthog_distinct_id: str | None = Field(default=None, max_length=120)


class QuizCreate(BaseModel):
    email: EmailStr
    answers: dict[str, Any]
    matched_coach_slug: str | None = Field(default=None, max_length=80)
    posthog_distinct_id: str | None = Field(default=None, max_length=120)


class LeadCreateResponse(BaseModel):
    id: UUID
