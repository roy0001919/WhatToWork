from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.registry import get_connector
from app.models.job_source import JobSource
from app.services.job_service import JobService


class JobSyncService:

    @staticmethod
    def sync_source(db: Session, source_id: int) -> dict:
        source = db.scalar(
            select(JobSource).where(
                JobSource.id == source_id,
                JobSource.enabled.is_(True),
            )
        )

        if source is None:
            raise ValueError(
                f"Enabled job source not found: {source_id}"
            )

        connector = get_connector(source.source_type)

        jobs = connector.fetch_and_normalize(
            source_id=source.id,
            source_metadata=source.source_metadata or {},
        )

        imported_count = 0

        for job_data in jobs:
            JobService.create_job(
                db=db,
                data=job_data,
            )
            imported_count += 1

        source.last_fetched_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(source)

        return {
            "source_id": source.id,
            "source_name": source.name,
            "fetched_count": len(jobs),
            "imported_count": imported_count,
            "last_fetched_at": source.last_fetched_at,
        }
