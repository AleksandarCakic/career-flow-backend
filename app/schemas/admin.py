"""Response shapes for the /admin/* read-only endpoints.

These are intentionally separate from the public-facing schemas so the
admin surface can expose internal fields (status, raw Stripe IDs, joined
coach slugs) without leaking them through the public API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import BookingStatus, LeadStatus, PaymentStatus


class AdminListResponse[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


class LeadUpdate(BaseModel):
    """Partial update for a lead. Both fields optional; unset = unchanged."""

    status: LeadStatus | None = None
    assigned_coach_id: UUID | None = Field(default=None)
    # Distinguishing "field absent" from "field is null" matters for
    # assigned_coach_id (null = unassign). Pydantic uses `model_fields_set`
    # at the route level to disambiguate.


class CoachAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    slug: str
    title: str
    bio_short: str
    bio_long: str
    headshot_url: str | None
    calendly_url: str
    is_active: bool
    sort_order: int
    created_at: datetime


class SuccessStoryCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=120)
    client_name: str = Field(min_length=1, max_length=200)
    client_role_before: str | None = Field(default=None, max_length=200)
    client_role_after: str | None = Field(default=None, max_length=200)
    client_company_after: str | None = Field(default=None, max_length=200)
    headshot_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    story_short: str = ""
    story_long: str | None = None
    coach_id: UUID | None = None
    is_featured: bool = False
    sort_order: int = 0
    published_at: datetime | None = None


class SuccessStoryUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    client_name: str | None = Field(default=None, min_length=1, max_length=200)
    client_role_before: str | None = Field(default=None, max_length=200)
    client_role_after: str | None = Field(default=None, max_length=200)
    client_company_after: str | None = Field(default=None, max_length=200)
    headshot_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    story_short: str | None = None
    story_long: str | None = None
    coach_id: UUID | None = None
    is_featured: bool | None = None
    sort_order: int | None = None
    published_at: datetime | None = None


class LeadAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    subject: str | None
    message: str | None
    source_page: str | None
    status: LeadStatus
    assigned_coach_id: UUID | None
    assigned_coach_slug: str | None
    created_at: datetime
    updated_at: datetime


class WaitlistAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    current_role: str
    years_of_experience: str
    biggest_challenge: str
    linkedin_profile: str | None
    coach_preference: str | None
    workshop_interests: list[str]
    status: str
    created_at: datetime
    updated_at: datetime


class QuizResponseAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    answers: dict[str, Any]
    matched_coach_id: UUID | None
    matched_coach_slug: str | None
    created_at: datetime


class BookingAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    calendly_event_uri: str
    coach_id: UUID | None
    coach_slug: str | None
    invitee_email: EmailStr
    invitee_name: str | None
    event_type: str | None
    scheduled_at: datetime
    status: BookingStatus
    lead_id: UUID | None
    created_at: datetime


class PaymentAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    stripe_payment_intent_id: str | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    stripe_checkout_session_id: str | None
    coach_id: UUID | None
    coach_slug: str | None
    package_id: UUID | None
    package_slug: str | None
    lead_id: UUID | None
    amount_cents: int
    amount_dollars: float
    currency: str
    status: PaymentStatus
    created_at: datetime


class SuccessStoryAdminRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    client_name: str
    client_role_before: str | None
    client_role_after: str | None
    client_company_after: str | None
    headshot_url: str | None
    linkedin_url: str | None
    story_short: str
    story_long: str | None
    coach_id: UUID | None
    coach_slug: str | None
    is_featured: bool
    sort_order: int
    published_at: datetime | None
    created_at: datetime
