from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
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
)
def add_unit(
    unit: UnitCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_unit(db, unit)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/", response_model=PaginatedResponse[UnitRead])
def list_units(db: Session = Depends(get_db)):
    return get_all_units(db)


@router.get("/{unit_id}", response_model=UnitRead)
def read_unit(
    unit_id: int,
    db: Session = Depends(get_db),
):
    unit_db = get_unit_by_id(db, unit_id)

    if unit_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found.",
        )

    return unit_db


@router.put("/{unit_id}", response_model=UnitRead)
def edit_unit(
    unit_id: int,
    unit: UnitUpdate,
    db: Session = Depends(get_db),
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


@router.delete("/{unit_id}")
def remove_unit(
    unit_id: int,
    db: Session = Depends(get_db),
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