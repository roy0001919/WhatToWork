from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)

    headline: Mapped[str | None] = mapped_column(String(500))
    years_experience: Mapped[int | None] = mapped_column()

    current_country: Mapped[str | None] = mapped_column(String(100))

    skills: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    preferred_roles: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    preferred_workplace_types: Mapped[list] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )

    employment_preferences: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    resume_text: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    analyses: Mapped[list["JobAnalysis"]] = relationship(
        back_populates="profile",
        cascade="all, delete-orphan",
    )
