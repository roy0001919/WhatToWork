from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


EligibilityStatus = Literal[
    "eligible",
    "potential",
    "uncertain",
    "excluded",
]


class JobAnalysisCreate(BaseModel):
    job_id: int
    profile_id: int

    technical_match_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    eligibility_status: EligibilityStatus = "uncertain"

    summary: str | None = None

    confidence: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    analysis_model: str | None = None
    prompt_version: str | None = None

    structured_result: dict = Field(default_factory=dict)


class JobAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    profile_id: int

    technical_match_score: int | None
    eligibility_status: EligibilityStatus

    summary: str | None
    confidence: float | None

    analysis_model: str | None
    prompt_version: str | None

    structured_result: dict

    analyzed_at: datetime
    created_at: datetime
