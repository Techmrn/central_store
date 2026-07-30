from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import math

from app.models.unit import Unit
from app.schemas.unit import UnitCreate, UnitUpdate
from app.core.constants import PAGE_SIZE


def create_unit(db: Session, unit: UnitCreate):

    name = unit.name.strip().title()
    symbol = unit.symbol.strip().upper()
    description = unit.description.strip() if unit.description else None

    existing_name = (
        db.query(Unit)
        .filter(
            func.lower(Unit.name) == name.lower(),
            Unit.is_active == True,
        )
        .first()
    )

    if existing_name:
        raise ValueError("Unit name already exists.")

    existing_symbol = (
        db.query(Unit)
        .filter(
            func.upper(Unit.symbol) == symbol,
            Unit.is_active == True,
        )
        .first()
    )

    if existing_symbol:
        raise ValueError("Unit symbol already exists.")

    db_unit = Unit(
        name=name,
        symbol=symbol,
        description=description,
    )

    db.add(db_unit)

    try:
        db.commit()
        db.refresh(db_unit)
        return db_unit

    except Exception:
        db.rollback()
        raise


def get_all_units( 

        db: Session, 
        search:str = "", # for search item
        page: int = 1, # for pagination
    ):

    query = db.query(Unit).filter(Unit.is_active == True) 

    if search:
        search = search.strip()

        query = query.filter(
            or_(

                Unit.name.ilike(f"%{search}%"), 
                Unit.symbol.ilike(f"%{search}%"), 
            )

        )

    total_records = query.count()

    units= ( 
        query

        .order_by(Unit.name)
        .offset((page-1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": units, 
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / PAGE_SIZE) if total_records else 1,
    }

def get_unit_by_id(db: Session, unit_id: int):

    return (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.is_active == True,
        )
        .first()
    )


def update_unit(
    db: Session,
    unit_id: int,
    unit: UnitUpdate,
):

    db_unit = (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.is_active == True,
        )
        .first()
    )

    if db_unit is None:
        return None

    update_data = unit.model_dump(exclude_unset=True)

    if "name" in update_data:

        name = update_data["name"].strip().title()

        duplicate = (
            db.query(Unit)
            .filter(
                func.lower(Unit.name) == name.lower(),
                Unit.id != unit_id,
                Unit.is_active == True,
            )
            .first()
        )

        if duplicate:
            raise ValueError("Unit name already exists.")

        db_unit.name = name

    if "symbol" in update_data:

        symbol = update_data["symbol"].strip().upper()

        duplicate = (
            db.query(Unit)
            .filter(
                func.upper(Unit.symbol) == symbol,
                Unit.id != unit_id,
                Unit.is_active == True,
            )
            .first()
        )

        if duplicate:
            raise ValueError("Unit symbol already exists.")

        db_unit.symbol = symbol

    if "description" in update_data:

        description = update_data["description"]

        db_unit.description = (
            description.strip()
            if description
            else None
        )

    try:
        db.commit()
        db.refresh(db_unit)
        return db_unit

    except Exception:
        db.rollback()
        raise


def delete_unit(
    db: Session,
    unit_id: int,
):

    db_unit = (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.is_active == True,
        )
        .first()
    )

    if db_unit is None:
        return None

    db_unit.is_active = False

    try:
        db.commit()
        db.refresh(db_unit)
        return db_unit

    except Exception:
        db.rollback()
        raise


#------------------For Drpdowns----------------

def get_unit_lookup(db: Session):

    return (
        db.query(Unit)
        .filter(Unit.is_active == True)
        .order_by(Unit.name)
        .all()
    )