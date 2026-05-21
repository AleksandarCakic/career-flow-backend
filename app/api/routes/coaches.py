from fastapi import APIRouter, HTTPException, status

from app.api.deps import DBSession
from app.schemas.coach import CoachRead
from app.services.coach_service import CoachService

router = APIRouter(prefix="/coaches", tags=["coaches"])


@router.get("", response_model=list[CoachRead])
async def list_coaches(db: DBSession) -> list[CoachRead]:
    service = CoachService(db)
    coaches = await service.list_active()
    return [CoachRead.model_validate(coach) for coach in coaches]


@router.get("/{slug}", response_model=CoachRead)
async def get_coach(slug: str, db: DBSession) -> CoachRead:
    service = CoachService(db)
    coach = await service.get_by_slug(slug)
    if not coach or not coach.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Coach not found")
    return CoachRead.model_validate(coach)
