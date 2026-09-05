from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import MovementType, TransactionSource, UnserviceableStatus, Category_Type, AssetStatus
from app.models.opening_stock import OpeningStock
from app.models.stock_movement import StockMovement
from app.models.item import Item
from app.models.category import Category
from app.models.asset import Asset
from app.models.unserviceable_material import UnserviceableMaterial
from app.services.scope_service import get_stock_office_id


def is_asset_item(db: Session, item_id: int) -> bool:
    """Return True when the Item belongs to an active ASSET category."""
    category_type = (
        db.query(Category.type)
        .join(Item, Item.category_id == Category.id)
        .filter(
            Item.id == item_id,
            Item.is_active == True,
            Category.is_active == True,
        )
        .scalar()
    )
    return category_type == Category_Type.ASSET

def get_available_asset_count(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
) -> int:
    """Count active, IN_STORE Assets for an Asset Item in the resolved store."""
    target_office_id = get_stock_office_id(db, office_id) if office_id is not None else None
    query = db.query(func.count(Asset.id)).join(Item, Asset.item_id == Item.id).join(
        Category, Item.category_id == Category.id
    ).filter(
        Asset.item_id == item_id,
        Asset.status == AssetStatus.IN_STORE,
        Asset.is_active == True,
        Item.is_active == True,
        Category.is_active == True,
        Category.type == Category_Type.ASSET,
    )
    if target_office_id is not None:
        query = query.filter(Asset.office_id == target_office_id)
    return int(query.scalar() or 0)


def get_item_stock(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
) -> float:
    """
    Calculate Total Physical Stock for an Item.
    Physical Stock = Opening Stock + Receipts + Returns + Transfer In + Adjustment In - Issues - Transfer Out - Adjustment Out
    Excludes historical audit transactions (transaction_source == HISTORICAL).
    Double-counting protection: If OPENING StockMovement exists for this FY, OpeningStock model is not added twice.
    """
    # Asset items are not quantity stock. Their availability is derived from
    # the Asset Register, so Stock Ledger balance for an Asset item is always 0.
    category_type = (
        db.query(Category.type)
        .join(Item, Item.category_id == Category.id)
        .filter(Item.id == item_id, Item.is_active == True, Category.is_active == True)
        .scalar()
    )
    if category_type == Category_Type.ASSET:
        return 0.0

    target_office_id = get_stock_office_id(db, office_id) if office_id is not None else None

    sm_query = db.query(
        func.coalesce(func.sum(StockMovement.quantity_in - StockMovement.quantity_out), 0)
    ).filter(
        StockMovement.item_id == item_id,
        StockMovement.is_active == True,
        StockMovement.transaction_source != TransactionSource.HISTORICAL,
    )

    if target_office_id is not None:
        sm_query = sm_query.filter(StockMovement.office_id == target_office_id)

    if financial_year_id is not None:
        sm_query = sm_query.filter(StockMovement.financial_year_id == financial_year_id)

    movement_balance = float(sm_query.scalar() or 0.0)

    has_opening_movement_query = db.query(StockMovement).filter(
        StockMovement.item_id == item_id,
        StockMovement.movement_type == MovementType.OPENING,
        StockMovement.is_active == True,
    )
    if target_office_id is not None:
        has_opening_movement_query = has_opening_movement_query.filter(StockMovement.office_id == target_office_id)
    if financial_year_id is not None:
        has_opening_movement_query = has_opening_movement_query.filter(StockMovement.financial_year_id == financial_year_id)

    has_opening_movement = has_opening_movement_query.first() is not None

    opening_balance = 0.0
    if not has_opening_movement:
        op_query = db.query(func.coalesce(func.sum(OpeningStock.quantity), 0)).filter(
            OpeningStock.item_id == item_id,
            OpeningStock.is_active == True,
        )
        if target_office_id is not None:
            op_query = op_query.filter(OpeningStock.office_id == target_office_id)
        if financial_year_id is not None:
            op_query = op_query.filter(OpeningStock.financial_year_id == financial_year_id)
        opening_balance = float(op_query.scalar() or 0.0)

    total_stock = opening_balance + movement_balance
    return round(total_stock, 2)


def get_item_unserviceable_stock(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
) -> float:
    """
    Calculate current active unserviceable material quantity for an Item.
    Includes materials currently in UNSERVICEABLE or UNDER_REPAIR status.
    Excludes REPAIRED, CONDEMNED, or DISPOSED materials.
    """
    category_type = (
        db.query(Category.type)
        .join(Item, Item.category_id == Category.id)
        .filter(Item.id == item_id, Item.is_active == True, Category.is_active == True)
        .scalar()
    )
    if category_type == Category_Type.ASSET:
        return 0.0

    target_office_id = get_stock_office_id(db, office_id) if office_id is not None else None

    un_query = db.query(
        func.coalesce(func.sum(UnserviceableMaterial.quantity), 0)
    ).filter(
        UnserviceableMaterial.item_id == item_id,
        UnserviceableMaterial.is_active == True,
        UnserviceableMaterial.status.in_([
            UnserviceableStatus.UNSERVICEABLE,
            UnserviceableStatus.UNDER_REPAIR,
        ]),
    )

    if target_office_id is not None:
        un_query = un_query.filter(UnserviceableMaterial.office_id == target_office_id)

    if financial_year_id is not None:
        un_query = un_query.filter(UnserviceableMaterial.financial_year_id == financial_year_id)

    unserviceable_qty = float(un_query.scalar() or 0.0)
    return round(unserviceable_qty, 2)


def get_item_usable_stock(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
) -> float:
    """
    Calculate Serviceable / Usable Stock for an Item.
    Usable Stock == Posted Stock Balance (usable_stock == current_stock).
    """
    return get_item_stock(
        db,
        item_id=item_id,
        office_id=office_id,
        financial_year_id=financial_year_id,
    )


def validate_stock_availability(
    db: Session,
    item_id: int,
    office_id: int,
    required_qty: float,
    financial_year_id: Optional[int] = None,
) -> bool:
    """
    Check if usable stock is >= required_qty.
    Raises ValueError if stock is insufficient.
    """
    if is_asset_item(db, item_id):
        raise ValueError(
            f"Stock validation is not applicable to Asset item ID {item_id}; "
            "validate individual Assets instead."
        )

    usable = get_item_usable_stock(
        db,
        item_id=item_id,
        office_id=office_id,
        financial_year_id=financial_year_id,
    )
    if usable < required_qty:
        raise ValueError(
            f"Insufficient stock for item ID {item_id}. Available stock: {usable}. Requested: {required_qty}."
        )

    return True

