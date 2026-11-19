from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job_source import (
    JobSourceCreate,
    JobSourceResponse,
)
from app.services.job_source_service import JobSourceService
from app.services.job_sync_service import JobSyncService


router = APIRouter(
    prefix="/api/v1/job-sources",
    tags=["Job Sources"],
)


@router.post(
    "",
    response_model=JobSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job source",
    description="Register a new job data source.",
)
def create_job_source(
    data: JobSourceCreate,
    db: Session = Depends(get_db),
) -> JobSourceResponse:
    return JobSourceService.create_job_source(
        db=db,
        data=data,
    )


@router.get(
    "",
    response_model=list[JobSourceResponse],
    summary="Get all job sources",
    description="Retrieve registered job sources with pagination.",
)
def get_job_sources(
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip.",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of records to return.",
    ),
    db: Session = Depends(get_db),
) -> list[JobSourceResponse]:
    return JobSourceService.get_job_sources(
        db=db,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/{source_id}/sync",
    summary="Synchronize jobs from a source",
    description="Fetch and import jobs from the specified enabled source.",
)
def sync_job_source(
    source_id: int,
    db: Session = Depends(get_db),
) -> dict:
    try:
        return JobSyncService.sync_source(
            db=db,
            source_id=source_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Job source synchronization failed.",
        ) from exc
