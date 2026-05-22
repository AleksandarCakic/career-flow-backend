from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    database_url: str = Field(default="postgresql+asyncpg://localhost/careerflow_dev")

    @field_validator("database_url")
    @classmethod
    def _ensure_asyncpg_driver(cls, v: str) -> str:
        # Managed Postgres providers expose bare "postgresql://" (or legacy
        # "postgres://"); SQLAlchemy 2.0 async requires the asyncpg driver.
        if v.startswith("postgresql+"):
            return v
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v.removeprefix("postgresql://")
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v.removeprefix("postgres://")
        return v

    sentry_dsn: str | None = None
    sentry_traces_sample_rate: float = 0.1

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    admin_emails: list[str] = Field(default_factory=list)

    clerk_secret_key: str = ""
    clerk_jwks_url: str = ""

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    calendly_webhook_signing_key: str = ""

    resend_api_key: str = ""
    resend_from_inquiry: str = "inquiry@career-flow.com"
    resend_from_noreply: str = "noreply@career-flow.com"
    resend_from_onboarding: str = "onboarding@career-flow.com"

    slack_webhook_leads: str = ""
    slack_webhook_bookings: str = ""
    slack_webhook_payments: str = ""
    slack_webhook_alerts: str = ""

    posthog_api_key: str = ""
    posthog_host: str = "https://eu.posthog.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
