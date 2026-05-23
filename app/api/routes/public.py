"""Public form-submission endpoints: contact, waitlist, quiz."""

import structlog
from fastapi import APIRouter, status

from app.api.deps import DBSession
from app.core.config import get_settings
from app.schemas.lead import (
    ContactCreate,
    LeadCreateResponse,
    QuizCreate,
    WaitlistCreate,
)
from app.services.email_service import EmailService
from app.services.lead_service import LeadService
from app.services.posthog_service import PostHogService
from app.services.slack_service import SlackChannel, SlackService

log = structlog.get_logger(__name__)

router = APIRouter(tags=["public"])


@router.post(
    "/contact",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_contact(payload: ContactCreate, db: DBSession) -> LeadCreateResponse:
    lead = await LeadService(db).create_contact(payload)
    settings = get_settings()

    await SlackService().post(
        SlackChannel.LEADS,
        text=f"📩 New contact from {payload.name} <{payload.email}> — {payload.subject}",
    )
    await EmailService().send(
        to=payload.email,
        from_address=settings.resend_from_inquiry,
        subject="Thanks for reaching out to Career Flow",
        html=(
            f"<p>Hi {payload.name},</p>"
            f"<p>Thanks for reaching out. We received your message about <strong>"
            f"{payload.subject}</strong> and will reply within one business day.</p>"
            f"<p>— The Career Flow team</p>"
        ),
    )
    await PostHogService().capture(
        distinct_id=payload.posthog_distinct_id or str(lead.id),
        event="lead.created",
        properties={
            "lead_id": str(lead.id),
            "source": "contact",
            "source_page": payload.source_page,
        },
    )

    return LeadCreateResponse(id=lead.id)


@router.post(
    "/waitlist",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_waitlist(payload: WaitlistCreate, db: DBSession) -> LeadCreateResponse:
    entry = await LeadService(db).create_waitlist(payload)
    settings = get_settings()

    await SlackService().post(
        SlackChannel.LEADS,
        text=(
            f"🎟️ New waitlist signup: {payload.email} | "
            f"{payload.current_role} | {payload.years_of_experience}"
        ),
    )
    await EmailService().send(
        to=payload.email,
        from_address=settings.resend_from_onboarding,
        subject="You're on the Career Flow waitlist",
        html=(
            "<p>Hi,</p>"
            "<p>You're on the list for the next Career Flow group coaching cohort. "
            "We open cohorts roughly every quarter — you'll get an email with first access "
            "as soon as the next one opens.</p>"
            "<p>— The Career Flow team</p>"
        ),
    )
    await PostHogService().capture(
        distinct_id=payload.posthog_distinct_id or str(entry.id),
        event="lead.created",
        properties={"lead_id": str(entry.id), "source": "waitlist"},
    )

    return LeadCreateResponse(id=entry.id)


@router.post(
    "/quiz",
    response_model=LeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_quiz(payload: QuizCreate, db: DBSession) -> LeadCreateResponse:
    response = await LeadService(db).create_quiz_response(payload)
    match_label = payload.matched_coach_slug or "no match"

    await SlackService().post(
        SlackChannel.LEADS,
        text=f"🧭 New quiz response from {payload.email} → matched: {match_label}",
    )
    await PostHogService().capture(
        distinct_id=payload.posthog_distinct_id or str(response.id),
        event="lead.created",
        properties={
            "lead_id": str(response.id),
            "source": "quiz",
            "matched_coach": match_label,
        },
    )

    return LeadCreateResponse(id=response.id)
