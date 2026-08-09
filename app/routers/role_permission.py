from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
from app.crud.role_permission import (
    create_role_permission,
    get_all_role_permissions,
    get_role_permission_by_id,
    delete_role_permission,
    bulk_assign_role_permissions,
)
from app.schemas.common import PaginatedResponse
from app.schemas.role_permission import (
    RolePermissionCreate,
    RolePermissionRead,
    RolePermissionDetail,
    RolePermissionBulkAssign,
)

router = APIRouter(
    prefix="/role-permissions",
    tags=["Role Permissions"],
)


@router.post(
    "/",
    response_model=RolePermissionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Role Permission Mapping",
)
def add_role_permission(
    data: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ROLE_PERMISSION_ASSIGN")),
):
    try:
        return create_role_permission(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/bulk",
    summary="Bulk Assign Permissions to Role",
)
def bulk_assign_permissions(
    data: RolePermissionBulkAssign,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ROLE_PERMISSION_ASSIGN")),
):
    try:
        return bulk_assign_role_permissions(
            db=db,
            role_id=data.role_id,
            permission_ids=data.permission_ids,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[RolePermissionDetail],
    summary="Get All Role Permissions",
)
def list_role_permissions(
    search: str = Query(default=""),
    role_id: int | None = Query(default=None),
    permission_id: int | None = Query(default=None),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ROLE_PERMISSION_VIEW")),
):
    return get_all_role_permissions(
        db=db,
        search=search,
        role_id=role_id,
        permission_id=permission_id,
        page=page,
    )


@router.get(
    "/{role_permission_id}",
    response_model=RolePermissionDetail,
    summary="Get Role Permission Mapping By ID",
)
def get_role_permission(
    role_permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ROLE_PERMISSION_VIEW")),
):
    item = get_role_permission_by_id(db, role_permission_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role permission mapping not found.",
        )
    return item


@router.delete(
    "/{role_permission_id}",
    summary="Delete Role Permission Mapping",
)
def remove_role_permission(
    role_permission_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ROLE_PERMISSION_REMOVE")),
):
    try:
        delete_role_permission(db, role_permission_id)
        return {
            "success": True,
            "message": "Role permission mapping deleted successfully.",
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
