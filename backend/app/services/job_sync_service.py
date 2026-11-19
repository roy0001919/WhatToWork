from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.greenhouse import GreenhouseConnector
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

        if source.source_type != "greenhouse":
            raise ValueError(
                f"Unsupported source type: {source.source_type}"
            )

        board_token = (source.source_metadata or {}).get("board_token")

        if not board_token:
            raise ValueError(
                f"Missing Greenhouse board token for source {source_id}"
            )

        jobs = GreenhouseConnector.fetch_and_normalize(
            board_token=board_token,
            source_id=source.id,
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
