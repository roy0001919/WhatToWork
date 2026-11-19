from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_type: str = Field(min_length=1, max_length=50)
    company_name: str | None = None
    base_url: str | None = None
    enabled: bool = True
    source_metadata: dict = Field(default_factory=dict)


class JobSourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    source_type: str | None = Field(default=None, max_length=50)
    company_name: str | None = None
    base_url: str | None = None
    enabled: bool | None = None
    source_metadata: dict | None = None


class JobSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    company_name: str | None
    base_url: str | None
    enabled: bool
    source_metadata: dict
    last_fetched_at: datetime | None
    created_at: datetime
    updated_at: datetime
