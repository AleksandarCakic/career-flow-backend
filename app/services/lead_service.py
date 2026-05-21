from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import Coach
from app.models.lead import Lead
from app.models.quiz_response import QuizResponse
from app.models.waitlist_entry import WaitlistEntry
from app.schemas.lead import ContactCreate, QuizCreate, WaitlistCreate


class LeadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_contact(self, payload: ContactCreate) -> Lead:
        lead = Lead(
            name=payload.name,
            email=payload.email,
            subject=payload.subject,
            message=payload.message,
            source_page=payload.source_page,
            posthog_distinct_id=payload.posthog_distinct_id,
        )
        self.db.add(lead)
        await self.db.commit()
        await self.db.refresh(lead)
        return lead

    async def create_waitlist(self, payload: WaitlistCreate) -> WaitlistEntry:
        entry = WaitlistEntry(
            email=payload.email,
            current_role=payload.current_role,
            years_of_experience=payload.years_of_experience,
            biggest_challenge=payload.biggest_challenge,
            linkedin_profile=payload.linkedin_profile,
            coach_preference=payload.coach_preference,
            workshop_interests=payload.workshop_interests,
            posthog_distinct_id=payload.posthog_distinct_id,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def create_quiz_response(self, payload: QuizCreate) -> QuizResponse:
        matched_coach_id = None
        if payload.matched_coach_slug:
            result = await self.db.execute(
                select(Coach).where(Coach.slug == payload.matched_coach_slug)
            )
            coach = result.scalar_one_or_none()
            if coach:
                matched_coach_id = coach.id
        response = QuizResponse(
            email=payload.email,
            answers=payload.answers,
            matched_coach_id=matched_coach_id,
            posthog_distinct_id=payload.posthog_distinct_id,
        )
        self.db.add(response)
        await self.db.commit()
        await self.db.refresh(response)
        return response
