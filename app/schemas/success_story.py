from pydantic import BaseModel, ConfigDict


class SuccessStoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    client_name: str
    client_role_before: str | None
    client_role_after: str | None
    client_company_after: str | None
    headshot_url: str | None
    linkedin_url: str | None
    story_short: str
    story_long: str | None
    is_featured: bool
    coach_slug: str | None = None
