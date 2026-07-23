from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.category import Category
from app.models.unit import Unit
from app.schemas.item import ItemCreate, ItemUpdate

def create_item(db: Session, item: ItemCreate):
    item_code = item.code.strip().upper()
    item_name = item.name.strip().title()

    duplicate = (
        db.query(Item).filter(
            Item.is_active == True,
            (
                (func.upper(Item.code) == item_code)
                |
                (func.lower(Item.name) == item_name.lower())
            ),
            
        ).first()
    )

    if duplicate:
        raise ValueError("Item with the same code or name already exists.")
    
    category = (
        db.query(Category)
        .filter(
            Category.id == item.category_id,
            Category.is_active == True,
        )
        .first()
    )

    if not category:
        raise ValueError("Category not found.")

    unit = (
        db.query(Unit)
        .filter(
            Unit.id == item.unit_id,
            Unit.is_active == True,
        )
        .first()
    )

    if not unit:
        raise ValueError("Unit not found.")

    db_item = Item(
        code=item_code,
        name=item_name,
        category_id=item.category_id,
        unit_id=item.unit_id,
        specification=item.specification.strip() if item.specification else None,
        remarks=item.remarks.strip() if item.remarks else None,
    )

    db.add(db_item)

    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception:
        db.rollback()
        raise


def get_all_items(db: Session):

    return (
        db.query(Item)
        .filter(Item.is_active == True)
        .order_by(Item.name)
        .all()
    )


def get_item_by_id(db: Session, item_id: int):

    return (
        db.query(Item)
        .filter(
            Item.id == item_id,
            Item.is_active == True,
        )
        .first()
    )


def update_item(
    db: Session,
    item_id: int,
    item: ItemUpdate,
):

    db_item = get_item_by_id(db, item_id)

    if not db_item:
        raise ValueError("Item not found.")

    if item.code:

        code = item.code.strip().upper()

        existing_code = (
            db.query(Item)
            .filter(
                func.upper(Item.code) == code,
                Item.id != item_id,
                Item.is_active == True,
            )
            .first()
        )

        if existing_code:
            raise ValueError("Item code already exists.")

        db_item.code = code

    if item.name:

        name = item.name.strip().title()

        existing_name = (
            db.query(Item)
            .filter(
                func.lower(Item.name) == name.lower(),
                Item.id != item_id,
                Item.is_active == True,
            )
            .first()
        )

        if existing_name:
            raise ValueError("Item name already exists.")

        db_item.name = name

    if item.category_id is not None:

        category = (
            db.query(Category)
            .filter(
                Category.id == item.category_id,
                Category.is_active == True,
            )
            .first()
        )

        if not category:
            raise ValueError("Category not found.")

        db_item.category_id = item.category_id

    if item.unit_id is not None:

        unit = (
            db.query(Unit)
            .filter(
                Unit.id == item.unit_id,
                Unit.is_active == True,
            )
            .first()
        )

        if not unit:
            raise ValueError("Unit not found.")

        db_item.unit_id = item.unit_id

    if item.specification is not None:
        db_item.specification = (
            item.specification.strip()
            if item.specification
            else None
        )

    if item.remarks is not None:
        db_item.remarks = (
            item.remarks.strip()
            if item.remarks
            else None
        )

    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception:
        db.rollback()
        raise


def delete_item(
    db: Session,
    item_id: int,
):

    db_item = get_item_by_id(db, item_id)

    if db_item is None:
        return None

    db_item.is_active = False

    try:
        db.commit()
        return db_item
    except Exception:
        db.rollback()
        raise