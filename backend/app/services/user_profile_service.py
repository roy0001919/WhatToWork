from sqlalchemy.orm import Session

from app.repositories.user_profile_repository import UserProfileRepository
from app.schemas.user_profile import UserProfileCreate, UserProfileUpdate


class UserProfileService:

    @staticmethod
    def create_profile(db: Session, data: UserProfileCreate):
        return UserProfileRepository.create(db=db, data=data)

    @staticmethod
    def get_profile(db: Session, profile_id: int):
        return UserProfileRepository.get_by_id(
            db=db,
            profile_id=profile_id,
        )

    @staticmethod
    def get_profiles(db: Session):
        return UserProfileRepository.get_all(db=db)

    @staticmethod
    def update_profile(
        db: Session,
        profile_id: int,
        data: UserProfileUpdate,
    ):
        profile = UserProfileRepository.get_by_id(
            db=db,
            profile_id=profile_id,
        )

        if profile is None:
            return None

        return UserProfileRepository.update(
            db=db,
            profile=profile,
            data=data,
        )

    @staticmethod
    def delete_profile(db: Session, profile_id: int) -> bool:
        profile = UserProfileRepository.get_by_id(
            db=db,
            profile_id=profile_id,
        )

        if profile is None:
            return False

        UserProfileRepository.delete(db=db, profile=profile)
        return True
