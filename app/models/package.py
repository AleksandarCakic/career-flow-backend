import enum

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class PackageTier(enum.StrEnum):
    NAVIGATOR = "navigator"
    ARCHITECT = "architect"
    ACCELERATOR = "accelerator"
    GROUP = "group"


class PricingModel(enum.StrEnum):
    SUBSCRIPTION_MONTHLY = "subscription_monthly"
    ONE_TIME = "one_time"


class Package(TimestampedBase):
    __tablename__ = "packages"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    tier: Mapped[PackageTier] = mapped_column(
        SAEnum(PackageTier, name="package_tier"), nullable=False
    )
    pricing_model: Mapped[PricingModel] = mapped_column(
        SAEnum(PricingModel, name="package_pricing_model"), nullable=False
    )
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False, default="")
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    starting_from: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stripe_product_id: Mapped[str | None] = mapped_column(String(120))
    stripe_price_id: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
