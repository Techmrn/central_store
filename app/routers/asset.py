from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.asset import (
    create_asset,
    create_asset_movement,
    delete_asset,
    get_all_assets,
    get_asset_by_asset_no,
    get_asset_by_id,
    get_asset_by_serial_no,
    get_asset_movements,
    update_asset,
)
from app.dependencies.permissions import require_permission
from app.models.enums import AssetStatus
from app.schemas.asset import (
    AssetCreate,
    AssetMovementCreate,
    AssetMovementRead,
    AssetRead,
    AssetUpdate,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(
    prefix="/assets",
    tags=["Assets"],
)


def _handle_value_error(e: ValueError):
    msg = str(e)
    if "already exists" in msg.lower():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )
    elif "not found" in msg.lower():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )


@router.post(
    "/",
    response_model=AssetRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Asset",
)
def add_asset(
    asset: AssetCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_CREATE")),
):
    try:
        return create_asset(db, asset)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[AssetRead],
    summary="Get All Assets",
)
def get_assets(
    search: str = "",
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    asset_status: Optional[AssetStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_VIEW")),
):
    return get_all_assets(
        db=db,
        search=search,
        item_id=item_id,
        office_id=office_id,
        section_id=section_id,
        status=asset_status,
        page=page,
    )


@router.get(
    "/by-asset-no/{asset_no}",
    response_model=AssetRead,
    summary="Get Asset By Asset No",
)
def get_asset_by_no(
    asset_no: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_VIEW")),
):
    asset = get_asset_by_asset_no(db, asset_no)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
    return asset


@router.get(
    "/by-serial-no/{serial_no}",
    response_model=AssetRead,
    summary="Get Asset By Serial No",
)
def get_asset_by_serial(
    serial_no: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_VIEW")),
):
    asset = get_asset_by_serial_no(db, serial_no)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
    return asset


@router.get(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Get Asset By ID",
)
def get_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_VIEW")),
):
    asset = get_asset_by_id(db, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
    return asset


@router.put(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Update Asset",
)
def edit_asset(
    asset_id: int,
    asset: AssetUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_UPDATE")),
):
    try:
        return update_asset(db, asset_id, asset)
    except ValueError as e:
        _handle_value_error(e)


@router.delete(
    "/{asset_id}",
    response_model=AssetRead,
    summary="Delete Asset",
)
def remove_asset(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_DELETE")),
):
    asset = delete_asset(db, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        )
    return asset


@router.post(
    "/{asset_id}/movements",
    response_model=AssetMovementRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record Asset Movement / Transfer",
)
def add_asset_movement(
    asset_id: int,
    movement: AssetMovementCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_MOVEMENT_CREATE")),
):
    try:
        return create_asset_movement(
            db=db,
            movement_in=movement,
            asset_id=asset_id,
        )
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/{asset_id}/movements",
    response_model=PaginatedResponse[AssetMovementRead],
    summary="Get Asset Movement History",
)
def get_movements_history(
    asset_id: int,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("ASSET_MOVEMENT_VIEW")),
):
    try:
        return get_asset_movements(
            db=db,
            asset_id=asset_id,
            page=page,
        )
    except ValueError as e:
        _handle_value_error(e)
