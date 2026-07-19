from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.unit import (
    create_unit,
    get_all_units,
    get_unit_by_id,
    update_unit,
    delete_unit
)   

from app.schemas.unit import (
    UnitCreate, 
    UnitRead,
    UnitUpdate
)

router = APIRouter(
    prefix="/units",
    tags=["Units"]
)

@router.post("/", response_model=UnitRead)
def add_unit(unit: UnitCreate, db: Session = Depends(get_db)):
    unit_db = create_unit(db, unit)

    if unit_db is False:
        raise HTTPException(
            status_code=409,
            detail="Unit already exists.",
        )
    return unit_db

@router.get("/", response_model=list[UnitRead])
def list_units(db: Session = Depends(get_db)):
    return get_all_units(db)

@router.get("/{unit_id}", response_model=UnitRead)
def read_unit(unit_id: int, db: Session = Depends(get_db)):
    unit_db = get_unit_by_id(db, unit_id)

    if not unit_db:
        raise HTTPException(
            status_code=404,
            detail="Unit not found",
        )
    return unit_db  

@router.put("/{unit_id}", response_model=UnitRead)
def edit_unit(unit_id: int, unit: UnitUpdate, db: Session = Depends(get_db)):
    result = update_unit(db, unit_id, unit)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Unit not found",
        )
    if result is False:
        raise HTTPException(
            status_code=409,
            detail="Unit already exists.",
        )
    return result

@router.delete("/{unit_id}")
def remove_unit(unit_id: int, db: Session = Depends(get_db)):
    result = delete_unit(db, unit_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Unit not found",
        )
    return {"message": "Unit deleted successfully."}