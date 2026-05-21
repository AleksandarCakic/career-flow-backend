from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedBase


class ResourceDownload(TimestampedBase):
    __tablename__ = "resource_downloads"

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    resource_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    download_token: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    posthog_distinct_id: Mapped[str | None] = mapped_column(String(120))
