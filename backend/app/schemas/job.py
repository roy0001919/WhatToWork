
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    source_id: int = Field(gt=0)
    external_id: str = Field(min_length=1, max_length=255)

    title: str = Field(min_length=1, max_length=255)
    company: str = Field(min_length=1, max_length=255)

    description: str | None = None
    location: str | None = None
    country: str | None = None

    workplace_type: str | None = None
    employment_type: str | None = None

    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    salary_currency: str | None = None

    source_url: str | None = None
    apply_url: str | None = None

    posted_at: datetime | None = None

    raw_data: dict = Field(default_factory=dict)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    external_id: str

    title: str
    company: str

    description: str | None
    location: str | None
    country: str | None

    workplace_type: str | None
    employment_type: str | None

    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None

    source_url: str | None
    apply_url: str | None

    posted_at: datetime | None
    first_seen_at: datetime
    last_seen_at: datetime

    is_active: bool

    raw_data: dict

    created_at: datetime
    updated_at: datetime


class JobSearchResponse(BaseModel):
    items: list[JobResponse]
    total: int
    skip: int
    limit: int
