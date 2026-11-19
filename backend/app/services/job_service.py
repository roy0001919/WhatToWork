from sqlalchemy.orm import Session

from app.repositories.job_repository import JobRepository
from app.schemas.job import JobCreate


class JobService:

    @staticmethod
    def create_job(db: Session, data: JobCreate):
        return JobRepository.create_or_update(
            db=db,
            data=data,
        )

    @staticmethod
    def get_job_by_id(db: Session, job_id: int):
        return JobRepository.get_by_id(
            db=db,
            job_id=job_id,
        )

    @staticmethod
    def get_jobs(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ):
        return JobRepository.get_all(
            db=db,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def search_jobs(
        db: Session,
        keyword: str | None = None,
        country: str | None = None,
        workplace_type: str | None = None,
        employment_type: str | None = None,
        source_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ):
        return JobRepository.search(
            db=db,
            keyword=keyword,
            country=country,
            workplace_type=workplace_type,
            employment_type=employment_type,
            source_id=source_id,
            skip=skip,
            limit=limit,
        )
