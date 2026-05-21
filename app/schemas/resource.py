from pydantic import BaseModel, EmailStr, Field


class ResourceRequestCreate(BaseModel):
    email: EmailStr
    consent: bool = Field(description="User explicit consent to receive the guide by email.")
    posthog_distinct_id: str | None = Field(default=None, max_length=120)


class ResourceRequestResponse(BaseModel):
    message: str
