"""Newsletter double opt-in endpoints.

POST /newsletter/subscribe → creates a pending row + sends a confirmation
email via Resend. GET /newsletter/confirm?token=… and /unsubscribe?token=…
mark the row accordingly. The frontend handles the page UX; backend just
validates and reports status.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import DBSession
from app.core.config import get_settings
from app.schemas.newsletter import (
    NewsletterConfirmResponse,
    NewsletterSubscribeRequest,
    NewsletterSubscribeResponse,
    NewsletterUnsubscribeResponse,
)
from app.services.email_service import EmailService
from app.services.newsletter_service import NewsletterService
from app.services.posthog_service import PostHogService

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.post(
    "/subscribe",
    response_model=NewsletterSubscribeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def subscribe(
    payload: NewsletterSubscribeRequest, db: DBSession
) -> NewsletterSubscribeResponse:
    settings = get_settings()
    row = await NewsletterService(db).create_pending(
        email=payload.email,
        source=payload.source,
        posthog_distinct_id=payload.posthog_distinct_id,
    )

    base = settings.public_web_url.rstrip("/")
    confirm_url = f"{base}/newsletter/confirm?token={row.confirmation_token}"
    await EmailService().send(
        to=row.email,
        from_address=settings.resend_from_onboarding,
        subject="Confirm your Career Flow newsletter subscription",
        html=(
            "<p>Hi,</p>"
            "<p>Thanks for subscribing to the Career Flow newsletter. Click the link below "
            "to confirm — once you do, you'll get an occasional note from us with career "
            "transition ideas, story breakdowns, and group-coaching openings.</p>"
            f'<p><a href="{confirm_url}">Confirm my subscription</a></p>'
            "<p>If you didn't subscribe, you can ignore this email — nothing happens until "
            "you click the link.</p>"
            "<p>— The Career Flow team</p>"
        ),
    )

    await PostHogService().capture(
        distinct_id=payload.posthog_distinct_id or str(row.id),
        event="newsletter.subscribe_requested",
        properties={
            "subscription_id": str(row.id),
            "source": payload.source,
        },
    )

    return NewsletterSubscribeResponse(status="pending_confirmation")


@router.get("/confirm", response_model=NewsletterConfirmResponse)
async def confirm(
    db: DBSession,
    token: str = Query(min_length=10, max_length=128),
) -> NewsletterConfirmResponse:
    service = NewsletterService(db)
    row = await service.find_by_token(token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Confirmation link is invalid or expired.",
        )
    if row.unsubscribed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="This subscription was already unsubscribed.",
        )
    newly_confirmed = await service.confirm(row)
    if newly_confirmed:
        await PostHogService().capture(
            distinct_id=row.posthog_distinct_id or str(row.id),
            event="newsletter.subscribe_confirmed",
            properties={"subscription_id": str(row.id)},
        )
        return NewsletterConfirmResponse(status="confirmed", email=row.email)
    return NewsletterConfirmResponse(status="already_confirmed", email=row.email)


@router.get("/unsubscribe", response_model=NewsletterUnsubscribeResponse)
async def unsubscribe(
    db: DBSession,
    token: str = Query(min_length=10, max_length=128),
) -> NewsletterUnsubscribeResponse:
    service = NewsletterService(db)
    row = await service.find_by_token(token)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unsubscribe link is invalid or expired.",
        )
    newly_unsubbed = await service.unsubscribe(row)
    if newly_unsubbed:
        await PostHogService().capture(
            distinct_id=row.posthog_distinct_id or str(row.id),
            event="newsletter.unsubscribed",
            properties={"subscription_id": str(row.id)},
        )
        return NewsletterUnsubscribeResponse(status="unsubscribed", email=row.email)
    return NewsletterUnsubscribeResponse(status="already_unsubscribed", email=row.email)
