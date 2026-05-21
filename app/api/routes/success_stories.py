from fastapi import APIRouter

from app.api.deps import DBSession
from app.schemas.success_story import SuccessStoryRead
from app.services.success_story_service import SuccessStoryService

router = APIRouter(prefix="/success-stories", tags=["success-stories"])


@router.get("", response_model=list[SuccessStoryRead])
async def list_success_stories(db: DBSession) -> list[SuccessStoryRead]:
    service = SuccessStoryService(db)
    rows = await service.list_published()
    return [
        SuccessStoryRead.model_validate({**story.__dict__, "coach_slug": coach_slug})
        for story, coach_slug in rows
    ]
