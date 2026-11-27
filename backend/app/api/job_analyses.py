from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job_analysis import JobAnalysisResponse
from app.schemas.job_dashboard import (
    DashboardAnalysisListResponse,
    EligibilityStatus,
)
from app.services.job_analysis_service import JobAnalysisService
from app.repositories.job_analysis_repository import JobAnalysisRepository


router = APIRouter(
    prefix="/api/v1/job-analyses",
    tags=["Job Analyses"],
)


@router.post(
    "/jobs/{job_id}/profiles/{profile_id}",
    response_model=JobAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def analyze_job(
    job_id: int,
    profile_id: int,
    db: Session = Depends(get_db),
):
    try:
        return JobAnalysisService.analyze_job(
            db=db,
            job_id=job_id,
            profile_id=profile_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.post(
    "/profiles/{profile_id}/batch",
    status_code=status.HTTP_200_OK,
)
def analyze_jobs(
    profile_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1, ge=1, le=5),
    db: Session = Depends(get_db),
):
    try:
        return JobAnalysisService.analyze_jobs(
            db=db,
            profile_id=profile_id,
            skip=skip,
            limit=limit,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        )


@router.get(
    "/profiles/{profile_id}",
    response_model=DashboardAnalysisListResponse,
)
def get_profile_analyses(
    profile_id: int,
    eligibility_status: EligibilityStatus | None = Query(default=None),
    search: str | None = Query(default=None, min_length=1, max_length=100),
    active_only: bool = Query(default=True),
    analysis_type: str = Query(
        default="all",
        pattern="^(all|genai|eligibility)$",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = JobAnalysisRepository.get_dashboard_analyses(
        db=db,
        profile_id=profile_id,
        eligibility_status=eligibility_status,
        search=search,
        active_only=active_only,
        skip=skip,
        limit=limit,
        analysis_type=analysis_type,
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{analysis_id}",
    response_model=JobAnalysisResponse,
)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
):
    analysis = JobAnalysisRepository.get_by_id(
        db=db,
        analysis_id=analysis_id,
    )

    if analysis is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job analysis not found",
        )

    return analysis
