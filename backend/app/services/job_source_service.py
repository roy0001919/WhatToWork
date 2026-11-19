from sqlalchemy.orm import Session

from app.repositories.job_source_repository import JobSourceRepository
from app.schemas.job_source import JobSourceCreate


class JobSourceService:

    @staticmethod
    def create_job_source(
        db: Session,
        data: JobSourceCreate,
    ):
        return JobSourceRepository.create(db, data)

    @staticmethod
    def get_job_sources(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ):
        return JobSourceRepository.get_all(
            db=db,
            skip=skip,
            limit=limit,
        )
