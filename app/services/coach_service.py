from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.coach import Coach


class CoachService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[Coach]:
        stmt = (
            select(Coach)
            .where(Coach.is_active.is_(True), Coach.deleted_at.is_(None))
            .order_by(Coach.sort_order, Coach.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Coach | None:
        stmt = select(Coach).where(Coach.slug == slug, Coach.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
