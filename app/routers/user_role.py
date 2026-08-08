from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.user_role import (
    create_user_role,
    get_all_user_roles,
    get_user_role_by_id,
    delete_user_role,
    bulk_assign_user_roles,
)
from app.schemas.common import PaginatedResponse
from app.schemas.user_role import (
    UserRoleCreate,
    UserRoleRead,
    UserRoleDetail,
    UserRoleBulkAssign,
)

router = APIRouter(
    prefix="/user-roles",
    tags=["User Roles"],
)


@router.post(
    "/",
    response_model=UserRoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Role Mapping",
)
def add_user_role(
    data: UserRoleCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_user_role(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/bulk",
    summary="Bulk Assign Roles to User",
)
def bulk_assign_roles(
    data: UserRoleBulkAssign,
    db: Session = Depends(get_db),
):
    try:
        return bulk_assign_user_roles(
            db=db,
            user_id=data.user_id,
            role_ids=data.role_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[UserRoleDetail],
    summary="Get All User Roles",
)
def list_user_roles(
    search: str = Query(default=""),
    user_id: int | None = Query(default=None),
    role_id: int | None = Query(default=None),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
):
    return get_all_user_roles(
        db=db,
        search=search,
        user_id=user_id,
        role_id=role_id,
        page=page,
    )


@router.get(
    "/{user_role_id}",
    response_model=UserRoleDetail,
    summary="Get User Role Mapping By ID",
)
def get_user_role(
    user_role_id: int,
    db: Session = Depends(get_db),
):
    item = get_user_role_by_id(db, user_role_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User role mapping not found.",
        )
    return item


@router.delete(
    "/{user_role_id}",
    summary="Delete User Role Mapping",
)
def remove_user_role(
    user_role_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_user_role(db, user_role_id)
        return {
            "success": True,
            "message": "User role mapping deleted successfully.",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
