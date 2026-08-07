from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.permission import (
    create_permission,
    delete_permission,
    get_all_permissions,
    get_permission_by_id,
    update_permission,
)
from app.schemas.common import PaginatedResponse
from app.schemas.permission import (
    PermissionCreate,
    PermissionRead,
    PermissionUpdate,
)

router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)


@router.post(
    "/",
    response_model=PermissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Permission",
)
def add_permission(
    permission: PermissionCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_permission(db, permission)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[PermissionRead],
    summary="Get All Permissions",
)
def list_permissions(
    search: str = Query(default=""),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
):
    return get_all_permissions(db, search=search, page=page)


@router.get(
    "/{permission_id}",
    response_model=PermissionRead,
    summary="Get Permission By ID",
)
def get_permission(
    permission_id: int,
    db: Session = Depends(get_db),
):
    db_permission = get_permission_by_id(db=db, permission_id=permission_id)
    if not db_permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permission not found.",
        )
    return db_permission


@router.put(
    "/{permission_id}",
    response_model=PermissionRead,
    summary="Update Permission",
)
def edit_permission(
    permission_id: int,
    permission: PermissionUpdate,
    db: Session = Depends(get_db),
):
    try:
        updated = update_permission(
            db=db,
            permission_id=permission_id,
            permission=permission,
        )
        if updated is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )
        return updated
    except ValueError as e:
        if str(e) == "Permission not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{permission_id}",
    summary="Delete Permission",
)
def remove_permission(
    permission_id: int,
    db: Session = Depends(get_db),
):
    try:
        deleted = delete_permission(db=db, permission_id=permission_id)
        if deleted is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Permission not found.",
            )
        return {
            "success": True,
            "message": "Permission deleted successfully.",
        }
    except ValueError as e:
        if str(e) == "Permission not found.":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
