from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import Coach
from app.models.success_story import SuccessStory


class SuccessStoryService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_published(
        self, featured_first: bool = True
    ) -> list[tuple[SuccessStory, str | None]]:
        """Returns published stories with the coach's slug joined in."""
        stmt = (
            select(SuccessStory, Coach.slug)
            .where(
                SuccessStory.deleted_at.is_(None),
                SuccessStory.published_at.is_not(None),
            )
            .outerjoin(Coach, Coach.id == SuccessStory.coach_id)
        )
        if featured_first:
            stmt = stmt.order_by(
                SuccessStory.is_featured.desc(),
                SuccessStory.sort_order,
                SuccessStory.created_at.desc(),
            )
        else:
            stmt = stmt.order_by(
                SuccessStory.sort_order,
                SuccessStory.created_at.desc(),
            )
        result = await self.db.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
