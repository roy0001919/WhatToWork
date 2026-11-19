from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileCreate(BaseModel):
    headline: str | None = None
    years_experience: int | None = Field(default=None, ge=0)
    current_country: str | None = None
    skills: list[str] = Field(default_factory=list)
    preferred_roles: list[str] = Field(default_factory=list)
    preferred_workplace_types: list[str] = Field(default_factory=list)
    employment_preferences: dict = Field(default_factory=dict)
    resume_text: str | None = None


class UserProfileUpdate(UserProfileCreate):
    pass


class UserProfileResponse(UserProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime