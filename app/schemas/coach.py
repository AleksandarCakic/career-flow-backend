from pydantic import BaseModel, ConfigDict


class CoachRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    name: str
    title: str
    bio_short: str
    bio_long: str
    headshot_url: str | None
    calendly_url: str
    sort_order: int
