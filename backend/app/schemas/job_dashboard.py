from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


EligibilityStatus = Literal[
    "eligible",
    "potential",
    "uncertain",
    "excluded",
]


class DashboardJobInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    company: str

    location: str | None
    country: str | None

    workplace_type: str | None
    employment_type: str | None

    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None

    source_url: str
    apply_url: str | None

    posted_at: datetime | None
    is_active: bool


class DashboardAnalysisItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    profile_id: int

    eligibility_status: EligibilityStatus
    technical_match_score: int | None
    summary: str | None
    confidence: float | None

    structured_result: dict

    analyzed_at: datetime
    job: DashboardJobInfo


class DashboardAnalysisListResponse(BaseModel):
    items: list[DashboardAnalysisItem]
    total: int
    skip: int
    limit: int
