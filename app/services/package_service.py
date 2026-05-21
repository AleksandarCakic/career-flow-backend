from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.package import Package


class PackageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_active(self) -> list[Package]:
        stmt = select(Package).where(Package.is_active.is_(True)).order_by(Package.amount_cents)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
