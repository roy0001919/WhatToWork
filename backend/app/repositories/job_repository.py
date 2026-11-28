from sqlalchemy import case, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.job import Job
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

        if keyword:
            pattern = f"%{keyword.strip()}%"
            conditions.append(
                or_(
                    Job.title.ilike(pattern),
                    Job.company.ilike(pattern),
                    Job.description.ilike(pattern),
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

        if keyword:
            relevance_order = case(
                (Job.title.ilike(pattern), 0),
                (Job.company.ilike(pattern), 1),
                else_=2,
            )
            ordering = (
                relevance_order,
                Job.created_at.desc(),
            )
        else:
            ordering = (Job.created_at.desc(),)

        statement = (
            select(Job)
            .where(*conditions)
            .order_by(*ordering)
            .offset(skip)
            .limit(limit)
        )

        jobs = list(db.scalars(statement).all())

        return jobs, total
