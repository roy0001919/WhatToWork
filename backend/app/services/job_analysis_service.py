from sqlalchemy.orm import Session

from app.analysis.eligibility_analyzer import EligibilityAnalyzer
from app.models.job_analysis import JobAnalysis
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.job_analysis import JobAnalysisCreate


class JobAnalysisService:

    @staticmethod
    def analyze_job(
        db: Session,
        job_id: int,
        profile_id: int,
    ) -> JobAnalysis:

        job = JobRepository.get_by_id(
            db=db,
            job_id=job_id,
        )

        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        profile = UserProfileRepository.get_by_id(
            db=db,
            profile_id=profile_id,
        )

        if profile is None:
            raise ValueError(f"User profile not found: {profile_id}")

        if not profile.current_country:
            raise ValueError("User profile current_country is required")

        result = EligibilityAnalyzer.analyze(
            description=job.description or "",
            current_country=profile.current_country,
            location=job.location,
            country=job.country,
            workplace_type=job.workplace_type,
        )

        analysis_data = JobAnalysisCreate(
            job_id=job.id,
            profile_id=profile.id,
            eligibility_status=result["status"],
            confidence=result["confidence"],
            summary=result["reason"],
            structured_result={
                "eligibility": result,
                "source": {
                    "job_id": job.id,
                    "job_title": job.title,
                    "company": job.company,
                    "source_url": job.source_url,
                },
                "job": {
                    "location": job.location,
                    "country": job.country,
                    "workplace_type": job.workplace_type,
                },
                "profile": {
                    "profile_id": profile.id,
                    "current_country": profile.current_country,
                },
            },
            analysis_model="rule-based",
            prompt_version="eligibility-v2",
        )

        return JobAnalysisRepository.upsert(
            db=db,
            data=analysis_data,
        )

    @staticmethod
    def analyze_jobs(
        db: Session,
        profile_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:

        profile = UserProfileRepository.get_by_id(
            db=db,
            profile_id=profile_id,
        )

        if profile is None:
            raise ValueError(f"User profile not found: {profile_id}")

        if not profile.current_country:
            raise ValueError("User profile current_country is required")

        jobs = JobRepository.get_all(
            db=db,
            skip=skip,
            limit=limit,
        )

        successful = []
        failed = []

        for job in jobs:
            try:
                analysis = JobAnalysisService.analyze_job(
                    db=db,
                    job_id=job.id,
                    profile_id=profile_id,
                )

                successful.append({
                    "job_id": job.id,
                    "analysis_id": analysis.id,
                    "eligibility_status": analysis.eligibility_status,
                })

            except Exception as error:
                db.rollback()

                failed.append({
                    "job_id": job.id,
                    "error": str(error),
                })

        return {
            "profile_id": profile_id,
            "total_jobs": len(jobs),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "successful": successful,
            "failed": failed,
        }
