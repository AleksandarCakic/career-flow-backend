from fastapi import APIRouter

from app.api.deps import DBSession
from app.schemas.package import PackageRead
from app.services.package_service import PackageService

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=list[PackageRead])
async def list_packages(db: DBSession) -> list[PackageRead]:
    service = PackageService(db)
    packages = await service.list_active()
    return [PackageRead.model_validate(pkg) for pkg in packages]
