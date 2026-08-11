from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.unserviceable import (
    create_unserviceable_material,
    transition_asset_unserviceable_status,
    update_unserviceable_material_status,
)
from app.dependencies.permissions import require_permission
from app.schemas.asset import AssetRead
from app.schemas.unserviceable import (
    AssetUnserviceableUpdate,
    UnserviceableMaterialCreate,
    UnserviceableMaterialRead,
    UnserviceableMaterialStatusUpdate,
)

router = APIRouter(
    prefix="/unserviceable",
    tags=["Unserviceable Register"],
)


def _handle_value_error(e: ValueError):
    msg = str(e)
    if "not found" in msg.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post(
    "/material",
    response_model=UnserviceableMaterialRead,
    status_code=status.HTTP_201_CREATED,
    summary="Mark Material Stock Quantity as Unserviceable",
)
def mark_material_unserviceable(
    data: UnserviceableMaterialCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNSERVICEABLE_CREATE")),
):
    try:
        return create_unserviceable_material(
            db=db,
            data=data,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        _handle_value_error(e)


@router.put(
    "/material/{unserviceable_id}/status",
    response_model=UnserviceableMaterialRead,
    summary="Update Unserviceable Material Disposition / Status",
)
def update_material_status(
    unserviceable_id: int,
    data: UnserviceableMaterialStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNSERVICEABLE_UPDATE")),
):
    try:
        return update_unserviceable_material_status(
            db=db,
            unserviceable_id=unserviceable_id,
            update_data=data,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        _handle_value_error(e)


@router.put(
    "/assets/{asset_id}/status",
    response_model=AssetRead,
    summary="Transition Asset Lifecycle Status (Unserviceable / Repair / Condemnation / Disposal)",
)
def update_asset_lifecycle_status(
    asset_id: int,
    data: AssetUnserviceableUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNSERVICEABLE_UPDATE")),
):
    try:
        return transition_asset_unserviceable_status(
            db=db,
            asset_id=asset_id,
            update_data=data,
            user_id=current_user.id if current_user else None,
        )
    except ValueError as e:
        _handle_value_error(e)
