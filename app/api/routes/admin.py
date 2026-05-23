"""Admin-only endpoints — paginated reads and partial-update writes across
every coach-managed entity. Every route is guarded by `require_admin`, which
checks the Clerk session token against the configured admin email allowlist.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.engine import Row
from sqlalchemy.exc import IntegrityError

from app.api.deps import DBSession
from app.core.security import AdminClaims
from app.models import (
    Booking,
    Coach,
    Lead,
    LeadStatus,
    Package,
    Payment,
    QuizResponse,
    SuccessStory,
    WaitlistEntry,
)
from app.schemas.admin import (
    AdminListResponse,
    BookingAdminRead,
    CoachAdminRead,
    LeadAdminRead,
    LeadUpdate,
    PaymentAdminRead,
    QuizResponseAdminRead,
    SuccessStoryAdminRead,
    SuccessStoryCreate,
    SuccessStoryUpdate,
    WaitlistAdminRead,
)
from app.services.posthog_service import PostHogService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[])

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


async def _count(session: Any, model: Any) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return int(result.scalar_one())


def _apply_lead_filters(
    stmt: Select[Any],
    status_filter: LeadStatus | None,
    search: str | None,
) -> Select[Any]:
    if status_filter is not None:
        stmt = stmt.where(Lead.status == status_filter)
    if search:
        # Parameterized ILIKE — safe against injection; SQLAlchemy escapes the
        # value. Match against both name and email so a user can type either.
        pattern = f"%{search}%"
        stmt = stmt.where(or_(Lead.name.ilike(pattern), Lead.email.ilike(pattern)))
    return stmt


@router.get("/leads", response_model=AdminListResponse[LeadAdminRead])
async def list_leads(
    session: DBSession,
    _claims: AdminClaims,
    limit: Limit = 50,
    offset: Offset = 0,
    status_filter: Annotated[LeadStatus | None, Query(alias="status")] = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
) -> AdminListResponse[LeadAdminRead]:
    base = select(Lead, Coach.slug.label("assigned_coach_slug")).outerjoin(
        Coach, Lead.assigned_coach_id == Coach.id
    )
    base = _apply_lead_filters(base, status_filter, search)
    page_stmt = base.order_by(Lead.created_at.desc()).offset(offset).limit(limit)
    rows = (await session.execute(page_stmt)).all()

    count_stmt = _apply_lead_filters(select(func.count()).select_from(Lead), status_filter, search)
    total = int((await session.execute(count_stmt)).scalar_one())

    return AdminListResponse[LeadAdminRead](
        items=[_lead_row(row) for row in rows],
        total=total,
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


# --- Write endpoints -----------------------------------------------------------


@router.get("/coaches", response_model=list[CoachAdminRead])
async def list_admin_coaches(
    session: DBSession,
    _claims: AdminClaims,
) -> list[CoachAdminRead]:
    """Every coach (active and inactive), excluding soft-deleted ones.

    Distinct from `GET /coaches`, which only returns active+ordered coaches
    for public marketing pages.
    """
    stmt = (
        select(Coach)
        .where(Coach.deleted_at.is_(None))
        .order_by(Coach.sort_order, Coach.name)
    )
    coaches = (await session.execute(stmt)).scalars().all()
    return [CoachAdminRead.model_validate(coach) for coach in coaches]


@router.patch("/leads/{lead_id}", response_model=LeadAdminRead)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    session: DBSession,
    _claims: AdminClaims,
) -> LeadAdminRead:
    lead = await session.get(Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    set_fields = payload.model_fields_set
    old_status = lead.status
    old_coach_id = lead.assigned_coach_id
    if "status" in set_fields and payload.status is not None:
        lead.status = payload.status
    if "assigned_coach_id" in set_fields:
        if payload.assigned_coach_id is not None:
            coach = await session.get(Coach, payload.assigned_coach_id)
            if coach is None or coach.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Coach not found.",
                )
        lead.assigned_coach_id = payload.assigned_coach_id
    if "notes" in set_fields:
        lead.notes = payload.notes
    await session.commit()
    await session.refresh(lead)

    # Analytics: fire after commit so we don't capture events for failed writes.
    posthog = PostHogService()
    distinct_id = lead.posthog_distinct_id or str(lead.id)
    if lead.status != old_status:
        await posthog.capture(
            distinct_id=distinct_id,
            event="lead.status_changed",
            properties={
                "lead_id": str(lead.id),
                "from_status": old_status.value,
                "to_status": lead.status.value,
            },
        )
    if lead.assigned_coach_id != old_coach_id:
        await posthog.capture(
            distinct_id=distinct_id,
            event="lead.assigned",
            properties={
                "lead_id": str(lead.id),
                "from_coach_id": str(old_coach_id) if old_coach_id else None,
                "to_coach_id": str(lead.assigned_coach_id) if lead.assigned_coach_id else None,
            },
        )

    slug: str | None = None
    if lead.assigned_coach_id is not None:
        coach = await session.get(Coach, lead.assigned_coach_id)
        slug = coach.slug if coach is not None else None
    return LeadAdminRead.model_validate({**lead.__dict__, "assigned_coach_slug": slug})


@router.post(
    "/success-stories",
    response_model=SuccessStoryAdminRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_success_story(
    payload: SuccessStoryCreate,
    session: DBSession,
    _claims: AdminClaims,
) -> SuccessStoryAdminRead:
    if payload.coach_id is not None:
        coach = await session.get(Coach, payload.coach_id)
        if coach is None or coach.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Coach not found.",
            )
    story = SuccessStory(**payload.model_dump())
    session.add(story)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already in use.",
        ) from exc
    await session.refresh(story)
    slug_for_coach: str | None = None
    if story.coach_id is not None:
        coach = await session.get(Coach, story.coach_id)
        slug_for_coach = coach.slug if coach is not None else None
    return SuccessStoryAdminRead.model_validate(
        {**story.__dict__, "coach_slug": slug_for_coach}
    )


@router.patch("/success-stories/{story_id}", response_model=SuccessStoryAdminRead)
async def update_success_story(
    story_id: UUID,
    payload: SuccessStoryUpdate,
    session: DBSession,
    _claims: AdminClaims,
) -> SuccessStoryAdminRead:
    story = await session.get(SuccessStory, story_id)
    if story is None or story.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Success story not found.",
        )
    updates = payload.model_dump(exclude_unset=True)
    if "coach_id" in updates and updates["coach_id"] is not None:
        coach = await session.get(Coach, updates["coach_id"])
        if coach is None or coach.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Coach not found.",
            )
    for field, value in updates.items():
        setattr(story, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Slug already in use.",
        ) from exc
    await session.refresh(story)
    slug_for_coach: str | None = None
    if story.coach_id is not None:
        coach = await session.get(Coach, story.coach_id)
        slug_for_coach = coach.slug if coach is not None else None
    return SuccessStoryAdminRead.model_validate(
        {**story.__dict__, "coach_slug": slug_for_coach}
    )


@router.delete("/success-stories/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_success_story(
    story_id: UUID,
    session: DBSession,
    _claims: AdminClaims,
) -> None:
    story = await session.get(SuccessStory, story_id)
    if story is None or story.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Success story not found.",
        )
    story.deleted_at = datetime.now(UTC)
    await session.commit()


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
