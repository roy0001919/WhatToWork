from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.user_profile import (
    UserProfileCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.user_profile_service import UserProfileService


router = APIRouter(
    prefix="/api/v1/user-profiles",
    tags=["User Profiles"],
)


@router.post(
    "",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    data: UserProfileCreate,
    db: Session = Depends(get_db),
):
    return UserProfileService.create_profile(db=db, data=data)


@router.get(
    "",
    response_model=list[UserProfileResponse],
)
def get_profiles(db: Session = Depends(get_db)):
    return UserProfileService.get_profiles(db=db)


@router.get(
    "/{profile_id}",
    response_model=UserProfileResponse,
)
def get_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    profile = UserProfileService.get_profile(
        db=db,
        profile_id=profile_id,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return profile


@router.put(
    "/{profile_id}",
    response_model=UserProfileResponse,
)
def update_profile(
    profile_id: int,
    data: UserProfileUpdate,
    db: Session = Depends(get_db),
):
    profile = UserProfileService.update_profile(
        db=db,
        profile_id=profile_id,
        data=data,
    )

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return profile


@router.delete(
    "/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_profile(
    profile_id: int,
    db: Session = Depends(get_db),
):
    deleted = UserProfileService.delete_profile(
        db=db,
        profile_id=profile_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    return None
