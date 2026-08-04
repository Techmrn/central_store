from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db

from app.crud.role import (
    create_role,
    get_all_roles,
    get_role_by_id,
    update_role,
    delete_role,
)


from app.schemas.common import PaginatedResponse
from app.schemas.role import (
    RoleCreate,
    RoleRead,
    RoleUpdate,
)

router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
)


@router.post(
    "/",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role",
)
def add_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_role(db, role)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[RoleRead],
    summary="Get All Roles",
)
def list_roles(
    db: Session = Depends(get_db),
):
    return get_all_roles(db)


@router.get(
    "/{role_id}",
    response_model=RoleRead,
    summary="Get Role By ID",
)
def get_role(
    role_id: int,
    db: Session = Depends(get_db),
):
    role_db = get_role_by_id(db, role_id)

    if not role_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    return role_db


@router.put(
    "/{role_id}",
    response_model=RoleRead,
    summary="Update Role",
)
def edit_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_role(
            db=db,
            role_id=role_id,
            role=role,
        )

    except ValueError as e:

        if str(e) == "Role not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{role_id}",
    summary="Delete Role",
)
def remove_role(
    role_id: int,
    db: Session = Depends(get_db),
):
    try:

        delete_role(
            db=db,
            role_id=role_id,
        )

        return {
            "success": True,
            "message": "Role deleted successfully.",
        }

    except ValueError as e:

        if str(e) == "Role not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )