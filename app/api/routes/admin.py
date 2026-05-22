"""Admin-only read endpoints — paginated lists across every coach-managed
entity. Every route is guarded by `require_admin`, which checks the Clerk
session token against the configured admin email allowlist.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.engine import Row

from app.api.deps import DBSession
from app.core.security import AdminClaims
from app.models import (
    Booking,
    Coach,
    Lead,
    Package,
    Payment,
    QuizResponse,
    SuccessStory,
    WaitlistEntry,
)
from app.schemas.admin import (
    AdminListResponse,
    BookingAdminRead,
    LeadAdminRead,
    PaymentAdminRead,
    QuizResponseAdminRead,
    SuccessStoryAdminRead,
    WaitlistAdminRead,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[])

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


async def _count(session: Any, model: Any) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


@router.get("/leads", response_model=AdminListResponse[LeadAdminRead])
async def list_leads(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[LeadAdminRead]:
    stmt = (
        select(Lead, Coach.slug.label("assigned_coach_slug"))
        .outerjoin(Coach, Lead.assigned_coach_id == Coach.id)
        .order_by(Lead.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items = [_lead_row(row) for row in rows]
    return AdminListResponse[LeadAdminRead](
        items=items,
        total=await _count(session, Lead),
        limit=limit,
        offset=offset,
    )


@router.get("/waitlist", response_model=AdminListResponse[WaitlistAdminRead])
async def list_waitlist(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[WaitlistAdminRead]:
    stmt = (
        select(WaitlistEntry)
        .order_by(WaitlistEntry.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return AdminListResponse[WaitlistAdminRead](
        items=[WaitlistAdminRead.model_validate(row) for row in rows],
        total=await _count(session, WaitlistEntry),
        limit=limit,
        offset=offset,
    )


@router.get("/quiz-responses", response_model=AdminListResponse[QuizResponseAdminRead])
async def list_quiz_responses(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[QuizResponseAdminRead]:
    stmt = (
        select(QuizResponse, Coach.slug.label("matched_coach_slug"))
        .outerjoin(Coach, QuizResponse.matched_coach_id == Coach.id)
        .order_by(QuizResponse.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items = [_quiz_row(row) for row in rows]
    return AdminListResponse[QuizResponseAdminRead](
        items=items,
        total=await _count(session, QuizResponse),
        limit=limit,
        offset=offset,
    )


@router.get("/bookings", response_model=AdminListResponse[BookingAdminRead])
async def list_bookings(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[BookingAdminRead]:
    stmt = (
        select(Booking, Coach.slug.label("coach_slug"))
        .outerjoin(Coach, Booking.coach_id == Coach.id)
        .order_by(Booking.scheduled_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items = [_booking_row(row) for row in rows]
    return AdminListResponse[BookingAdminRead](
        items=items,
        total=await _count(session, Booking),
        limit=limit,
        offset=offset,
    )


@router.get("/payments", response_model=AdminListResponse[PaymentAdminRead])
async def list_payments(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[PaymentAdminRead]:
    stmt = (
        select(
            Payment,
            Coach.slug.label("coach_slug"),
            Package.slug.label("package_slug"),
        )
        .outerjoin(Coach, Payment.coach_id == Coach.id)
        .outerjoin(Package, Payment.package_id == Package.id)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items = [_payment_row(row) for row in rows]
    return AdminListResponse[PaymentAdminRead](
        items=items,
        total=await _count(session, Payment),
        limit=limit,
        offset=offset,
    )


@router.get("/success-stories", response_model=AdminListResponse[SuccessStoryAdminRead])
async def list_success_stories(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
) -> AdminListResponse[SuccessStoryAdminRead]:
    stmt = (
        select(SuccessStory, Coach.slug.label("coach_slug"))
        .outerjoin(Coach, SuccessStory.coach_id == Coach.id)
        .where(SuccessStory.deleted_at.is_(None))
        .order_by(SuccessStory.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    items = [_story_row(row) for row in rows]
    total_stmt = (
        select(func.count())
        .select_from(SuccessStory)
        .where(SuccessStory.deleted_at.is_(None))
    )
    total = int((await session.execute(total_stmt)).scalar_one())
    return AdminListResponse[SuccessStoryAdminRead](
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# --- Row → schema adapters -----------------------------------------------------


def _lead_row(row: Row[Any]) -> LeadAdminRead:
    lead: Lead = row[0]
    slug: str | None = row[1]
    return LeadAdminRead.model_validate({**lead.__dict__, "assigned_coach_slug": slug})


def _quiz_row(row: Row[Any]) -> QuizResponseAdminRead:
    quiz: QuizResponse = row[0]
    slug: str | None = row[1]
    return QuizResponseAdminRead.model_validate({**quiz.__dict__, "matched_coach_slug": slug})


def _booking_row(row: Row[Any]) -> BookingAdminRead:
    booking: Booking = row[0]
    slug: str | None = row[1]
    return BookingAdminRead.model_validate({**booking.__dict__, "coach_slug": slug})


def _payment_row(row: Row[Any]) -> PaymentAdminRead:
    payment: Payment = row[0]
    coach_slug: str | None = row[1]
    package_slug: str | None = row[2]
    return PaymentAdminRead.model_validate(
        {
            **payment.__dict__,
            "coach_slug": coach_slug,
            "package_slug": package_slug,
            "amount_dollars": payment.amount_cents / 100,
        }
    )


def _story_row(row: Row[Any]) -> SuccessStoryAdminRead:
    story: SuccessStory = row[0]
    slug: str | None = row[1]
    return SuccessStoryAdminRead.model_validate({**story.__dict__, "coach_slug": slug})
