from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job_analysis import JobAnalysisResponse
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
    limit: int = Query(default=100, ge=1, le=500),
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
    response_model=list[JobAnalysisResponse],
)
def get_profile_analyses(
    profile_id: int,
    db: Session = Depends(get_db),
):
    return JobAnalysisRepository.get_by_profile(
        db=db,
        profile_id=profile_id,
    )


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
