"""Response shapes for the /admin/* read-only endpoints.

These are intentionally separate from the public-facing schemas so the
admin surface can expose internal fields (status, raw Stripe IDs, joined
coach slugs) without leaking them through the public API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models import BookingStatus, LeadStatus, PaymentStatus


class AdminListResponse[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


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
