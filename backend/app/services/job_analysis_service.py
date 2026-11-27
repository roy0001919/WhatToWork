from sqlalchemy.orm import Session

from app.analysis.eligibility_analyzer import EligibilityAnalyzer
from app.analysis.security_eligibility_analyzer import (
    SecurityEligibilityAnalyzer,
)
from app.core.config import settings
from app.models.job_analysis import JobAnalysis
from app.repositories.job_analysis_repository import JobAnalysisRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.job_analysis import JobAnalysisCreate
from app.services.genai_job_analyzer import (
    GenAIJobAnalyzer,
    PROMPT_VERSION,
)
from app.services.recommendation_policy import RecommendationPolicy


class JobAnalysisService:

    @staticmethod
    def analyze_job_eligibility_only(
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
            title=job.title,
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
    def analyze_job(
        db: Session,
        job_id: int,
        profile_id: int,
    ) -> JobAnalysis:
        return JobAnalysisService.analyze_job_with_genai(
            db=db,
            job_id=job_id,
            profile_id=profile_id,
        )

    @staticmethod
    def analyze_job_with_genai(
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

        # Only send the explicitly selected, de-identified fields.
        # Never send resume_text or personal contact information.
        safe_profile = {
            "headline": profile.headline,
            "years_experience": profile.years_experience,
            "skills": profile.skills or [],
            "preferred_roles": profile.preferred_roles or [],
            "preferred_workplace_types": (
                profile.preferred_workplace_types or []
            ),
            "employment_preferences": (
                profile.employment_preferences or []
            ),
        }

        safe_job = {
            "title": job.title,
            "company": job.company,
            "description": job.description or "",
            "location": job.location,
            "country": job.country,
            "workplace_type": job.workplace_type,
            "employment_type": job.employment_type,
            "salary_min": float(job.salary_min) if job.salary_min is not None else None,
            "salary_max": float(job.salary_max) if job.salary_max is not None else None,
            "salary_currency": job.salary_currency,
        }

        # 1. GenAI job intelligence
        genai_result = GenAIJobAnalyzer.analyze(
            job=safe_job,
            profile=safe_profile,
        )

        # 2. Deterministic location and work eligibility
        eligibility_result = EligibilityAnalyzer.analyze(
            description=job.description or "",
            current_country=profile.current_country,
            location=job.location,
            country=job.country,
            workplace_type=job.workplace_type,
            title=job.title,
        )

        # 3. Security clearance and export control detection
        security_result = SecurityEligibilityAnalyzer.analyze(
            description=job.description or "",
        )

        # 4. Apply deterministic recommendation policy
        recommendation_result = RecommendationPolicy.evaluate(
            genai_result=genai_result,
            eligibility_result=eligibility_result,
            security_result=security_result,
        )

        structured_result = {
            "genai": genai_result,
            "eligibility": eligibility_result,
            "security_eligibility": security_result,
            "recommendation": recommendation_result,
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
                "employment_type": job.employment_type,
                "salary_min": float(job.salary_min) if job.salary_min is not None else None,
                "salary_max": float(job.salary_max) if job.salary_max is not None else None,
                "salary_currency": job.salary_currency,
            },
            "profile": {
                "profile_id": profile.id,
                "current_country": profile.current_country,
            },
        }

        analysis_data = JobAnalysisCreate(
            job_id=job.id,
            profile_id=profile.id,
            technical_match_score=genai_result[
                "technical_match_score"
            ],
            eligibility_status=eligibility_result["status"],
            confidence=eligibility_result["confidence"],
            summary=genai_result["summary"],
            structured_result=structured_result,
            analysis_model=settings.gemini_model,
            prompt_version=PROMPT_VERSION,
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
        limit: int = 1,
    ) -> dict:

        if not 1 <= limit <= 5:
            raise ValueError(
                "Batch analysis limit must be between 1 and 5."
            )

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
