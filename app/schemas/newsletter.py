from pydantic import BaseModel, EmailStr, Field


class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr
    source: str | None = Field(default=None, max_length=80)
    posthog_distinct_id: str | None = Field(default=None, max_length=120)


class NewsletterSubscribeResponse(BaseModel):
    status: str  # "pending_confirmation"


class NewsletterConfirmResponse(BaseModel):
    status: str  # "confirmed" or "already_confirmed"
    email: EmailStr


class NewsletterUnsubscribeResponse(BaseModel):
    status: str  # "unsubscribed" or "already_unsubscribed"
    email: EmailStr
