from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobAnalysis(Base):
    __tablename__ = "job_analyses"

    __table_args__ = (
        CheckConstraint(
            "technical_match_score IS NULL OR "
            "(technical_match_score >= 0 AND technical_match_score <= 100)",
            name="ck_job_analysis_match_score",
        ),
        CheckConstraint(
            "eligibility_status IN "
            "('eligible', 'potential', 'uncertain', 'excluded')",
            name="ck_job_analysis_eligibility_status",
        ),
        UniqueConstraint(
            "job_id",
            "profile_id",
            name="uq_job_analyses_job_profile",
        ),
        Index("ix_job_analyses_job_id", "job_id"),
        Index("ix_job_analyses_profile_id", "profile_id"),
        Index("ix_job_analyses_eligibility_status", "eligibility_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )

    profile_id: Mapped[int] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    technical_match_score: Mapped[int | None] = mapped_column(Integer)

    eligibility_status: Mapped[str] = mapped_column(
        String(20),
        default="uncertain",
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(Text)

    confidence: Mapped[float | None] = mapped_column()

    analysis_model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))

    structured_result: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job: Mapped["Job"] = relationship()

    profile: Mapped["UserProfile"] = relationship(
        back_populates="analyses",
    )
