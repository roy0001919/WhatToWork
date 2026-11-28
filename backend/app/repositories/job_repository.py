import re

from sqlalchemy import case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.job_analysis import JobAnalysis
from app.schemas.job import JobCreate


class JobRepository:

    @staticmethod
    def create_or_update(db: Session, data: JobCreate) -> Job:
        values = data.model_dump()

        statement = insert(Job).values(**values)

        update_values = {
            key: getattr(statement.excluded, key)
            for key in values
            if key not in {"source_id", "external_id"}
        }

        update_values["last_seen_at"] = func.now()
        update_values["updated_at"] = func.now()

        statement = (
            statement
            .on_conflict_do_update(
                constraint="uq_jobs_source_external_id",
                set_=update_values,
            )
            .returning(Job)
        )

        try:
            job = db.scalars(statement).one()
            db.commit()
            db.refresh(job)
            return job
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(db: Session, job_id: int) -> Job | None:
        statement = select(Job).where(Job.id == job_id)
        return db.scalar(statement)

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Job]:
        statement = (
            select(Job)
            .where(Job.is_active.is_(True))
            .order_by(Job.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def search(
        db: Session,
        keyword: str | None = None,
        country: str | None = None,
        workplace_type: str | None = None,
        employment_type: str | None = None,
        source_id: int | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Job], int]:

        conditions = [Job.is_active.is_(True)]
        word_pattern = None

        if keyword and keyword.strip():
            normalized_keyword = re.escape(keyword.strip())
            word_pattern = rf"\m{normalized_keyword}\M"

            conditions.append(
                or_(
                    Job.title.op("~*")(word_pattern),
                    Job.company.op("~*")(word_pattern),
                    Job.description.op("~*")(word_pattern),
                )
            )

        if country:
            conditions.append(
                Job.country.ilike(f"%{country.strip()}%")
            )

        if workplace_type:
            conditions.append(
                Job.workplace_type.ilike(
                    f"%{workplace_type.strip()}%"
                )
            )

        if employment_type:
            normalized_employment_type = (
                employment_type.strip()
                .lower()
                .replace("_", "-")
                .replace(" ", "-")
            )

            normalized_db_employment_type = func.replace(
                func.replace(
                    func.lower(Job.employment_type),
                    "_",
                    "-",
                ),
                " ",
                "-",
            )

            conditions.append(
                normalized_db_employment_type.ilike(
                    f"%{normalized_employment_type}%"
                )
            )

        if source_id is not None:
            conditions.append(Job.source_id == source_id)

        count_statement = (
            select(func.count())
            .select_from(Job)
            .where(*conditions)
        )

        total = db.scalar(count_statement) or 0

        if word_pattern:
            relevance_order = case(
                (Job.title.op("~*")(word_pattern), 0),
                (Job.company.op("~*")(word_pattern), 1),
                else_=2,
            )

            ordering = (
                relevance_order,
                Job.created_at.desc(),
                Job.id.desc(),
            )
        else:
            ordering = (
                Job.created_at.desc(),
                Job.id.desc(),
            )

        statement = (
            select(Job)
            .where(*conditions)
            .order_by(*ordering)
            .offset(skip)
            .limit(limit)
        )

        jobs = list(db.scalars(statement).all())

        return jobs, total

    @staticmethod
    def get_dashboard_jobs(
        db: Session,
        profile_id: int,
        keyword: str | None = None,
        eligibility_status: str | None = None,
        analysis_type: str = "all",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[tuple[Job, JobAnalysis | None]], int]:

        if analysis_type not in {"all", "genai", "eligibility"}:
            raise ValueError("Invalid analysis_type")

        conditions = [Job.is_active.is_(True)]

        if analysis_type == "genai":
            conditions.append(
                JobAnalysis.structured_result.has_key("genai")
            )
        elif analysis_type == "eligibility":
            conditions.append(
                ~JobAnalysis.structured_result.has_key("genai")
            )

        if eligibility_status:
            conditions.append(
                JobAnalysis.eligibility_status == eligibility_status
            )

        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Job.title.ilike(pattern),
                    Job.company.ilike(pattern),
                )
            )

        join_condition = (
            (JobAnalysis.job_id == Job.id)
            & (JobAnalysis.profile_id == profile_id)
        )

        count_statement = (
            select(func.count())
            .select_from(Job)
            .outerjoin(JobAnalysis, join_condition)
            .where(*conditions)
        )

        total = db.scalar(count_statement) or 0

        statement = (
            select(Job, JobAnalysis)
            .outerjoin(JobAnalysis, join_condition)
            .where(*conditions)
            .order_by(Job.created_at.desc(), Job.id.desc())
            .offset(skip)
            .limit(limit)
        )

        items = list(db.execute(statement).all())

        return items, total

