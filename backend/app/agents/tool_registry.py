from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.agent import AgentToolResult
from app.services.job_service import JobService
from app.services.job_analysis_service import JobAnalysisService


class ToolRegistry:
    MAX_SEARCH_LIMIT = 20
    MAX_DESCRIPTION_LENGTH = 3000

    TOOL_DECLARATIONS = [
        {
            "name": "search_jobs",
            "description": (
                "Search active job listings. For worldwide or international "
                "remote searches, omit country unless the user explicitly "
                "specifies a job location. The country argument means the "
                "job's location, never the candidate's residence. Keyword "
                "uses substring matching, so prefer broad terms such as "
                "'Python' instead of a complete job title. You can make "
                "multiple searches with different keywords. Each call "
                "returns at most 20 jobs. Use skip for pagination and "
                "inspect total to determine whether more results exist."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "keyword": {
                        "type": "STRING",
                        "description": (
                            "A broad job title, skill, or company keyword. "
                            "Uses substring matching against job title, "
                            "company, and description. Prefer broad terms "
                            "such as Python or Backend over long exact "
                            "job titles. Optional."
                        ),
                    },
                    "country": {
                        "type": "STRING",
                        "description": (
                            "The country where the job is located, not the "
                            "candidate's current residence. Only provide "
                            "this when the user explicitly requests jobs "
                            "in a particular country or market. Omit for "
                            "worldwide searches. Optional."
                        ),
                    },
                    "workplace_type": {
                        "type": "STRING",
                        "description": (
                            "Workplace type filter: remote, hybrid, or onsite. "
                            "Use remote when the user requests remote jobs. "
                            "Optional."
                        ),
                    },
                    "employment_type": {
                        "type": "STRING",
                        "description": (
                            "Employment type filter, such as full-time or "
                            "contract. Only apply when requested or clearly "
                            "required by the user's criteria. Optional."
                        ),
                    },
                    "limit": {
                        "type": "INTEGER",
                        "description": (
                            "Maximum number of jobs to return in this call. "
                            "Must be between 1 and 20. Use 20 when collecting "
                            "a broad candidate pool."
                        ),
                    },
                    "skip": {
                        "type": "INTEGER",
                        "description": (
                            "Pagination offset. Use 0 for the first page, "
                            "then increase by the previous page's returned "
                            "count to retrieve subsequent pages. Do not "
                            "repeat an already retrieved page."
                        ),
                    },
                },
                "required": [],
            },
        },
        {
            "name": "get_job_details",
            "description": "Get details of a specific job by its ID.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "job_id": {
                        "type": "INTEGER",
                        "description": "The job ID.",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "check_eligibility",
            "description": (
                "Check whether the user's profile country is eligible "
                "for a specific job."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "job_id": {
                        "type": "INTEGER",
                        "description": "The job ID.",
                    },
                },
                "required": ["job_id"],
            },
        },
        {
            "name": "analyze_job",
            "description": (
                "Perform full AI job analysis including skill matching, "
                "location eligibility, security requirements, and recommendation."
            ),
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "job_id": {
                        "type": "INTEGER",
                        "description": "The job ID.",
                    },
                },
                "required": ["job_id"],
            },
        },
    ]

    @classmethod
    def get_declarations(cls) -> list[dict[str, Any]]:
        return cls.TOOL_DECLARATIONS

    @classmethod
    def execute(
        cls,
        name: str,
        arguments: dict[str, Any],
        db: Session,
        profile_id: int,
    ) -> AgentToolResult:

        handlers = {
            "search_jobs": cls._search_jobs,
            "get_job_details": cls._get_job_details,
            "check_eligibility": cls._check_eligibility,
            "analyze_job": cls._analyze_job,
        }

        handler = handlers.get(name)

        if handler is None:
            return AgentToolResult(
                name=name,
                success=False,
                error="Unknown tool.",
            )

        try:
            result = handler(
                arguments=arguments,
                db=db,
                profile_id=profile_id,
            )

            return AgentToolResult(
                name=name,
                success=True,
                result=result,
            )

        except (ValueError, TypeError) as error:
            return AgentToolResult(
                name=name,
                success=False,
                error=str(error),
            )

        except Exception:
            db.rollback()

            return AgentToolResult(
                name=name,
                success=False,
                error="Tool execution failed.",
            )

    @staticmethod
    def _validate_arguments(
        arguments: dict[str, Any],
        allowed: set[str],
        required: set[str] | None = None,
    ) -> None:

        if not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object.")

        unexpected = set(arguments) - allowed

        if unexpected:
            raise ValueError(
                f"Unsupported arguments: {', '.join(sorted(unexpected))}"
            )

        missing = (required or set()) - set(arguments)

        if missing:
            raise ValueError(
                f"Missing required arguments: {', '.join(sorted(missing))}"
            )

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)

        if isinstance(value, (datetime, date)):
            return value.isoformat()

        return value

    @classmethod
    def _serialize_job(cls, job: Any, include_description: bool = False) -> dict:
        result = {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "country": job.country,
            "workplace_type": job.workplace_type,
            "employment_type": job.employment_type,
            "salary_min": cls._serialize_value(job.salary_min),
            "salary_max": cls._serialize_value(job.salary_max),
            "salary_currency": job.salary_currency,
            "source_url": job.source_url,
            "apply_url": job.apply_url,
            "posted_at": cls._serialize_value(job.posted_at),
        }

        if include_description:
            result["description"] = (
                (job.description or "")[:cls.MAX_DESCRIPTION_LENGTH]
            )

        return result

    @classmethod
    def _serialize_analysis(cls, analysis: Any) -> dict:
        return {
            "analysis_id": analysis.id,
            "job_id": analysis.job_id,
            "profile_id": analysis.profile_id,
            "eligibility_status": analysis.eligibility_status,
            "technical_match_score": analysis.technical_match_score,
            "confidence": cls._serialize_value(analysis.confidence),
            "summary": analysis.summary,
            "structured_result": analysis.structured_result,
        }

    @classmethod
    def _search_jobs(
        cls,
        arguments: dict,
        db: Session,
        profile_id: int,
    ) -> dict:

        cls._validate_arguments(
            arguments,
            allowed={
                "keyword",
                "country",
                "workplace_type",
                "employment_type",
                "limit",
                "skip",
            },
        )

        limit = arguments.get("limit", 10)
        skip = arguments.get("skip", 0)

        if type(limit) is not int or not 1 <= limit <= cls.MAX_SEARCH_LIMIT:
            raise ValueError("Search limit must be between 1 and 20.")

        if type(skip) is not int or not 0 <= skip <= 10000:
            raise ValueError("Search offset must be between 0 and 10000.")

        for field in (
            "keyword",
            "country",
            "workplace_type",
            "employment_type",
        ):
            value = arguments.get(field)

            if value is not None:
                if not isinstance(value, str) or len(value) > 200:
                    raise ValueError(f"Invalid {field}.")

        jobs, total = JobService.search_jobs(
            db=db,
            keyword=arguments.get("keyword"),
            country=arguments.get("country"),
            workplace_type=arguments.get("workplace_type"),
            employment_type=arguments.get("employment_type"),
            skip=skip,
            limit=limit,
        )

        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "items": [
                cls._serialize_job(job)
                for job in jobs
            ],
        }

    @classmethod
    def _get_job_details(
        cls,
        arguments: dict,
        db: Session,
        profile_id: int,
    ) -> dict:

        cls._validate_arguments(
            arguments,
            allowed={"job_id"},
            required={"job_id"},
        )

        job_id = arguments["job_id"]

        if type(job_id) is not int or job_id <= 0:
            raise ValueError("Invalid job_id.")

        job = JobService.get_job_by_id(
            db=db,
            job_id=job_id,
        )

        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        return cls._serialize_job(
            job,
            include_description=True,
        )

    @classmethod
    def _check_eligibility(
        cls,
        arguments: dict,
        db: Session,
        profile_id: int,
    ) -> dict:

        cls._validate_arguments(
            arguments,
            allowed={"job_id"},
            required={"job_id"},
        )

        job_id = arguments["job_id"]

        if type(job_id) is not int or job_id <= 0:
            raise ValueError("Invalid job_id.")

        analysis = JobAnalysisService.analyze_job_eligibility_only(
            db=db,
            job_id=job_id,
            profile_id=profile_id,
        )

        return cls._serialize_analysis(analysis)

    @classmethod
    def _analyze_job(
        cls,
        arguments: dict,
        db: Session,
        profile_id: int,
    ) -> dict:

        cls._validate_arguments(
            arguments,
            allowed={"job_id"},
            required={"job_id"},
        )

        job_id = arguments["job_id"]

        if type(job_id) is not int or job_id <= 0:
            raise ValueError("Invalid job_id.")

        analysis = JobAnalysisService.analyze_job(
            db=db,
            job_id=job_id,
            profile_id=profile_id,
        )

        return cls._serialize_analysis(analysis)
