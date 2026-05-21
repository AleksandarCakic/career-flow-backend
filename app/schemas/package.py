from pydantic import BaseModel, ConfigDict

from app.models.package import PackageTier, PricingModel


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    tier: PackageTier
    pricing_model: PricingModel
    amount_cents: int
    currency: str
    description: str
    features: list[str]
    starting_from: bool
