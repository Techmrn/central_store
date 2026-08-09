from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
from app.crud.unit import (
    create_unit,
    get_all_units,
    get_unit_by_id,
    update_unit,
    delete_unit,
)

from app.schemas.common import PaginatedResponse
from app.schemas.unit import (
    UnitCreate,
    UnitRead,
    UnitUpdate,
)

router = APIRouter(
    prefix="/units",
    tags=["Units"],
)


@router.post(
    "/",
    response_model=UnitRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Unit",
)
def add_unit(
    unit: UnitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNIT_CREATE")),
):
    try:
        return create_unit(db, unit)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[UnitRead],
    summary="Get All Units",
)
def list_units(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNIT_VIEW")),
):
    return get_all_units(db)


@router.get(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Get Unit By ID",
)
def read_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNIT_VIEW")),
):
    unit_db = get_unit_by_id(db, unit_id)

    if unit_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found.",
        )

    return unit_db


@router.put(
    "/{unit_id}",
    response_model=UnitRead,
    summary="Update Unit",
)
def edit_unit(
    unit_id: int,
    unit: UnitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNIT_UPDATE")),
):
    try:
        result = update_unit(db, unit_id, unit)

        if result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found.",
            )

        return result

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{unit_id}",
    summary="Delete Unit",
)
def remove_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("UNIT_DELETE")),
):
    result = delete_unit(db, unit_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found.",
        )

    return {
        "success": True,
        "message": "Unit deleted successfully.",
    }