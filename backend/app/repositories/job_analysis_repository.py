from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.job import Job
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
    def get_dashboard_analyses(
        db: Session,
        profile_id: int,
        eligibility_status: str | None = None,
        search: str | None = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 20,
        analysis_type: str = "all",
    ) -> tuple[list[JobAnalysis], int]:
        """
        Retrieve job analyses with job information for Dashboard.

        analysis_type:
            all         - All analyses
            genai       - Analyses containing GenAI results
            eligibility - Eligibility-only analyses
        """
        if analysis_type not in {"all", "genai", "eligibility"}:
            raise ValueError(f"Invalid analysis_type: {analysis_type}")

        statement = (
            select(JobAnalysis)
            .join(JobAnalysis.job)
            .options(joinedload(JobAnalysis.job))
            .where(JobAnalysis.profile_id == profile_id)
        )

        count_statement = (
            select(func.count(JobAnalysis.id))
            .join(JobAnalysis.job)
            .where(JobAnalysis.profile_id == profile_id)
        )

        if analysis_type == "genai":
            analysis_filter = JobAnalysis.structured_result.has_key("genai")
            statement = statement.where(analysis_filter)
            count_statement = count_statement.where(analysis_filter)

        elif analysis_type == "eligibility":
            analysis_filter = ~JobAnalysis.structured_result.has_key("genai")
            statement = statement.where(analysis_filter)
            count_statement = count_statement.where(analysis_filter)

        if eligibility_status:
            statement = statement.where(
                JobAnalysis.eligibility_status == eligibility_status
            )
            count_statement = count_statement.where(
                JobAnalysis.eligibility_status == eligibility_status
            )

        if active_only:
            statement = statement.where(Job.is_active.is_(True))
            count_statement = count_statement.where(
                Job.is_active.is_(True)
            )

        if search:
            search_pattern = f"%{search.strip()}%"
            search_filter = or_(
                Job.title.ilike(search_pattern),
                Job.company.ilike(search_pattern),
            )
            statement = statement.where(search_filter)
            count_statement = count_statement.where(search_filter)

        total = db.scalar(count_statement) or 0

        statement = (
            statement
            .order_by(
                JobAnalysis.analyzed_at.desc(),
                JobAnalysis.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )

        items = list(db.scalars(statement).all())

        return items, total

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
