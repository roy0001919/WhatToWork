from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_analysis import JobAnalysis
from app.schemas.job_analysis import JobAnalysisCreate


class JobAnalysisRepository:

    @staticmethod
    def create(db: Session, data: JobAnalysisCreate) -> JobAnalysis:
        analysis = JobAnalysis(**data.model_dump())

        try:
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            return analysis
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(
        db: Session,
        analysis_id: int,
    ) -> JobAnalysis | None:
        statement = select(JobAnalysis).where(
            JobAnalysis.id == analysis_id
        )
        return db.scalar(statement)

    @staticmethod
    def get_latest_by_job_and_profile(
        db: Session,
        job_id: int,
        profile_id: int,
    ) -> JobAnalysis | None:
        statement = (
            select(JobAnalysis)
            .where(
                JobAnalysis.job_id == job_id,
                JobAnalysis.profile_id == profile_id,
            )
            .order_by(
                JobAnalysis.analyzed_at.desc(),
                JobAnalysis.id.desc(),
            )
            .limit(1)
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_profile(
        db: Session,
        profile_id: int,
    ) -> list[JobAnalysis]:
        statement = (
            select(JobAnalysis)
            .where(JobAnalysis.profile_id == profile_id)
            .order_by(
                JobAnalysis.analyzed_at.desc(),
                JobAnalysis.id.desc(),
            )
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def get_by_job(
        db: Session,
        job_id: int,
    ) -> list[JobAnalysis]:
        statement = (
            select(JobAnalysis)
            .where(JobAnalysis.job_id == job_id)
            .order_by(
                JobAnalysis.analyzed_at.desc(),
                JobAnalysis.id.desc(),
            )
        )
        return list(db.scalars(statement).all())
