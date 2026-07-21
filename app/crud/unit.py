from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.unit import Unit
from app.schemas.unit import UnitCreate, UnitUpdate


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


def get_all_units(db: Session):

    return (
        db.query(Unit)
        .filter(Unit.is_active == True)
        .order_by(Unit.name)
        .all()
    )


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