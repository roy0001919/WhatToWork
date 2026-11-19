from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job_analysis import JobAnalysis
from app.schemas.job_analysis import JobAnalysisCreate


class JobAnalysisRepository:

    @staticmethod
    def upsert(db: Session, data: JobAnalysisCreate) -> JobAnalysis:
        """
        Create a new analysis or update the existing analysis
        for the same job and profile.
        """
        analysis_data = data.model_dump()

        try:
            analysis = db.scalar(
                select(JobAnalysis)
                .where(
                    JobAnalysis.job_id == analysis_data["job_id"],
                    JobAnalysis.profile_id == analysis_data["profile_id"],
                )
                .with_for_update()
            )

            if analysis is None:
                analysis = JobAnalysis(**analysis_data)
                db.add(analysis)
            else:
                for key, value in analysis_data.items():
                    setattr(analysis, key, value)

            db.commit()
            db.refresh(analysis)
            return analysis

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def create(db: Session, data: JobAnalysisCreate) -> JobAnalysis:
        """Backward-compatible wrapper."""
        return JobAnalysisRepository.upsert(db, data)

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
