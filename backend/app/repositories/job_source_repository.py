from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_source import JobSource
from app.schemas.job_source import JobSourceCreate


class JobSourceRepository:

    @staticmethod
    def create(db: Session, data: JobSourceCreate) -> JobSource:
        job_source = JobSource(**data.model_dump())

        db.add(job_source)
        db.commit()
        db.refresh(job_source)

        return job_source

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> list[JobSource]:
        statement = (
            select(JobSource)
            .order_by(JobSource.id.asc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(statement).all())
