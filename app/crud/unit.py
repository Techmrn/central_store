"""
CRUD operations for Unit Master.

This module contains all database operations related to the Unit master table.

Responsibilities:
    - Create Unit
    - List Units
    - Get Unit by ID
    - Update Unit
    - Soft Delete Unit

Business Rules:
    1. Unit name must be unique (case-insensitive).
    2. Unit symbol must be unique (case-insensitive).
    3. Only active units are returned.
    4. Delete is a Soft Delete (is_active=False).
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.unit import Unit
from app.schemas.unit import UnitCreate, UnitUpdate


# ==========================================================
# Create Unit
# ==========================================================

def create_unit(db: Session, unit: UnitCreate):
    """
    Create a new Unit.

    Returns
    -------
    Unit
        Newly created Unit object.

    False
        If another active unit already exists with the
        same name or symbol.
    """

    # -----------------------------------------
    # Normalize user input
    # -----------------------------------------

    normalized_name = unit.name.strip().lower()

    # Keep original capitalization for the name
    display_name = unit.name.strip()

    # Store symbol in uppercase
    normalized_symbol = unit.symbol.strip().upper()

    # -----------------------------------------
    # Duplicate Name Check
    # -----------------------------------------

    existing_name = (
        db.query(Unit)
        .filter(
            func.lower(func.trim(Unit.name)) == normalized_name,
            Unit.is_active == True,
        )
        .first()
    )

    if existing_name:
        return False

    # -----------------------------------------
    # Duplicate Symbol Check
    # -----------------------------------------

    existing_symbol = (
        db.query(Unit)
        .filter(
            func.upper(func.trim(Unit.symbol)) == normalized_symbol,
            Unit.is_active == True,
        )
        .first()
    )

    if existing_symbol:
        return False

    # -----------------------------------------
    # Create Unit Object
    # -----------------------------------------

    db_unit = Unit(
        name=display_name,
        symbol=normalized_symbol,
        description=unit.description,
    )

    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)

    return db_unit


# ==========================================================
# Get All Units
# ==========================================================

def get_all_units(db: Session):
    """
    Return all active units.
    """

    return (
        db.query(Unit)
        .filter(Unit.is_active == True)
        .order_by(Unit.name)
        .all()
    )


# ==========================================================
# Get Unit by ID
# ==========================================================

def get_unit_by_id(db: Session, unit_id: int):
    """
    Return a single active Unit by ID.

    Returns None if not found.
    """

    return (
        db.query(Unit)
        .filter(
            Unit.id == unit_id,
            Unit.is_active == True,
        )
        .first()
    )


# ==========================================================
# Update Unit
# ==========================================================

def update_unit(
    db: Session,
    unit_id: int,
    unit: UnitUpdate,
):
    """
    Update an existing Unit.

    Returns
    -------
    Unit
        Updated Unit object.

    None
        Unit not found.

    False
        Duplicate name or symbol exists.
    """

    # -----------------------------------------
    # Find Existing Active Unit
    # -----------------------------------------

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

    # -----------------------------------------
    # Normalize User Input
    # -----------------------------------------

    normalized_name = unit.name.strip().lower()
    display_name = unit.name.strip()

    normalized_symbol = unit.symbol.strip().upper()

    # -----------------------------------------
    # Duplicate Name Check
    # -----------------------------------------

    duplicate_name = (
        db.query(Unit)
        .filter(
            func.lower(func.trim(Unit.name)) == normalized_name,
            Unit.id != unit_id,
            Unit.is_active == True,
        )
        .first()
    )

    if duplicate_name:
        return False

    # -----------------------------------------
    # Duplicate Symbol Check
    # -----------------------------------------

    duplicate_symbol = (
        db.query(Unit)
        .filter(
            func.upper(func.trim(Unit.symbol)) == normalized_symbol,
            Unit.id != unit_id,
            Unit.is_active == True,
        )
        .first()
    )

    if duplicate_symbol:
        return False

    # -----------------------------------------
    # Update Object
    # -----------------------------------------

    db_unit.name = display_name
    db_unit.symbol = normalized_symbol
    db_unit.description = unit.description

    db.commit()
    db.refresh(db_unit)

    return db_unit


# ==========================================================
# Delete Unit (Soft Delete)
# ==========================================================

def delete_unit(db: Session, unit_id: int):
    """
    Soft delete a Unit.

    Returns
    -------
    Unit
        Updated Unit object.

    None
        Unit not found.
    """

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

    db.commit()
    db.refresh(db_unit)

    return db_unit