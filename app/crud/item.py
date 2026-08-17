from datetime import datetime
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
import math
from typing import Optional

from app.models.item import Item
from app.models.category import Category
from app.models.unit import Unit
from app.schemas.item import ItemCreate, ItemUpdate
from app.core.constants import PAGE_SIZE


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
        is_temporary=getattr(item, "is_temporary", False) or False,
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


def create_temporary_item(
    db: Session,
    name: str,
    category_id: int,
    unit_id: int,
    code: Optional[str] = None,
    specification: Optional[str] = None,
    remarks: Optional[str] = None,
) -> Item:
    """
    Create a Local Purchase / Temporary item for non-catalogue goods receipt.
    Generates a unique LP- code if none provided.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Item name is required.")

    category = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
    if not category:
        raise ValueError("Category not found.")

    unit = db.query(Unit).filter(Unit.id == unit_id, Unit.is_active == True).first()
    if not unit:
        raise ValueError("Unit not found.")

    if code and code.strip():
        clean_code = code.strip().upper()
    else:
        # Generate sequential LP-YYYYMMDD-XXXX code
        today_str = datetime.now().strftime("%Y%m%d")
        prefix = f"LP-{today_str}-"
        count = db.query(Item).filter(Item.code.like(f"{prefix}%")).count()
        clean_code = f"{prefix}{count + 1:04d}"

    # Check code uniqueness
    existing = db.query(Item).filter(func.upper(Item.code) == clean_code.upper(), Item.is_active == True).first()
    if existing:
        # Append random suffix if conflict
        import uuid
        clean_code = f"LP-{uuid.uuid4().hex[:6].upper()}"

    db_item = Item(
        code=clean_code,
        name=clean_name,
        category_id=category_id,
        unit_id=unit_id,
        is_temporary=True,
        specification=specification.strip() if specification else None,
        remarks=remarks.strip() if remarks else "Local Purchase / Non-Catalogue Item",
    )

    db.add(db_item)
    try:
        db.commit()
        db.refresh(db_item)
        return db_item
    except Exception:
        db.rollback()
        raise


def promote_temporary_item(
    db: Session,
    item_id: int,
    code: Optional[str] = None,
    name: Optional[str] = None,
    category_id: Optional[int] = None,
    unit_id: Optional[int] = None,
) -> Item:
    """
    Promote a temporary/local purchase item to a permanent catalogue item.
    Preserves item_id and all historical StockMovements.
    """
    item = get_item_by_id(db, item_id)
    if not item:
        raise ValueError("Item not found.")

    if not item.is_temporary:
        raise ValueError("Item is already a permanent catalogue item.")

    if code and code.strip():
        clean_code = code.strip().upper()
        existing = db.query(Item).filter(
            func.upper(Item.code) == clean_code,
            Item.id != item_id,
            Item.is_active == True,
        ).first()
        if existing:
            raise ValueError(f"Item code '{clean_code}' already exists in catalogue.")
        item.code = clean_code

    if name and name.strip():
        clean_name = name.strip().title()
        existing_name = db.query(Item).filter(
            func.lower(Item.name) == clean_name.lower(),
            Item.id != item_id,
            Item.is_active == True,
        ).first()
        if existing_name:
            raise ValueError(f"Item name '{clean_name}' already exists in catalogue.")
        item.name = clean_name

    if category_id is not None:
        cat = db.query(Category).filter(Category.id == category_id, Category.is_active == True).first()
        if not cat:
            raise ValueError("Category not found.")
        item.category_id = category_id

    if unit_id is not None:
        u = db.query(Unit).filter(Unit.id == unit_id, Unit.is_active == True).first()
        if not u:
            raise ValueError("Unit not found.")
        item.unit_id = unit_id

    item.is_temporary = False

    try:
        db.commit()
        db.refresh(item)
        return item
    except Exception:
        db.rollback()
        raise


def get_all_items(
    db: Session,
    search: str = "",
    page: int = 1,
    include_temporary: bool = False,
    is_temporary: Optional[bool] = None,
):
    query = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .join(Unit, Item.unit_id == Unit.id)
        .filter(
            Item.is_active == True,
            Category.is_active == True,
            Unit.is_active == True,
        )
    )

    if is_temporary is not None:
        query = query.filter(Item.is_temporary == is_temporary)
    elif not include_temporary:
        query = query.filter(Item.is_temporary == False)

    if search:
        search = search.strip()
        query = query.filter(
            or_(
                Item.code.ilike(f"%{search}%"),
                Item.name.ilike(f"%{search}%"),
                Category.name.ilike(f"%{search}%"),
                Unit.name.ilike(f"%{search}%"),
            )
        )

    total_records = query.count()

    items = (
        query
        .order_by(Item.name)
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
        .all()
    )

    return {
        "items": items,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": math.ceil(total_records / PAGE_SIZE) if total_records else 1,
    }


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

    if item.is_temporary is not None:
        db_item.is_temporary = item.is_temporary

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