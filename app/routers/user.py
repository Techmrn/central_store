"""
Starter for app/routers/user.py

Endpoints:
POST    /users/
GET     /users/
GET     /users/{user_id}
PUT     /users/{user_id}
DELETE  /users/{user_id}

Match the style of role.py.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.crud.user import (
    create_user,
    get_all_users,
    get_user_by_id,
    update_user,
    delete_user,
)

from app.schemas.user import (
    UserCreate,
    UserRead,
    UserUpdate,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
)
def add_user(
    user: UserCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_user(db, user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[UserRead],
    summary="Get All Users",
)
def list_users(
    db: Session = Depends(get_db),
):
    return get_all_users(db)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get User By ID",
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
):

    db_user = get_user_by_id(
        db=db,
        user_id=user_id,
    )

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return db_user


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Update User",
)
def edit_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
):

    try:

        return update_user(
            db=db,
            user_id=user_id,
            user=user,
        )

    except ValueError as e:

        if str(e) == "User not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{user_id}",
    summary="Delete User",
)
def remove_user(
    user_id: int,
    db: Session = Depends(get_db),
):

    try:

        delete_user(
            db=db,
            user_id=user_id,
        )

        return {
            "success": True,
            "message": "User deleted successfully.",
        }

    except ValueError as e:

        if str(e) == "User not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )