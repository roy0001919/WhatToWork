from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class UserProfileRepository:

    @staticmethod
    def create(db: Session, data: UserProfileCreate) -> UserProfile:
        profile = UserProfile(**data.model_dump())

        try:
            db.add(profile)
            db.commit()
            db.refresh(profile)
            return profile
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_by_id(db: Session, profile_id: int) -> UserProfile | None:
        statement = select(UserProfile).where(
            UserProfile.id == profile_id
        )
        return db.scalar(statement)

    @staticmethod
    def get_all(db: Session) -> list[UserProfile]:
        statement = select(UserProfile).order_by(
            UserProfile.created_at.desc()
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def update(
        db: Session,
        profile: UserProfile,
        data: UserProfileUpdate,
    ) -> UserProfile:
        update_data = data.model_dump(exclude_unset=True)

        try:
            for key, value in update_data.items():
                setattr(profile, key, value)

            db.commit()
            db.refresh(profile)
            return profile
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def delete(db: Session, profile: UserProfile) -> None:
        try:
            db.delete(profile)
            db.commit()
        except Exception:
            db.rollback()
            raise
