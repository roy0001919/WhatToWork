from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import (
    JobCreate,
    JobResponse,
    JobSearchResponse,
)
from app.services.job_service import JobService


router = APIRouter(
    prefix="/api/v1/jobs",
    tags=["Jobs"],
)


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job",
)
def create_job(
    data: JobCreate,
    db: Session = Depends(get_db),
) -> JobResponse:
    return JobService.create_job(
        db=db,
        data=data,
    )


@router.get(
    "",
    response_model=JobSearchResponse,
    summary="Search jobs",
)
def get_jobs(
    keyword: str | None = Query(default=None),
    country: str | None = Query(default=None),
    workplace_type: str | None = Query(default=None),
    employment_type: str | None = Query(default=None),
    source_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> JobSearchResponse:
    jobs, total = JobService.search_jobs(
        db=db,
        keyword=keyword,
        country=country,
        workplace_type=workplace_type,
        employment_type=employment_type,
        source_id=source_id,
        skip=skip,
        limit=limit,
    )

    return JobSearchResponse(
        items=jobs,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get job by ID",
)
def get_job_by_id(
    job_id: int,
    db: Session = Depends(get_db),
) -> JobResponse:
    job = JobService.get_job_by_id(
        db=db,
        job_id=job_id,
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return job
