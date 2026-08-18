from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import MovementType, TransactionSource, UnserviceableStatus
from app.models.opening_stock import OpeningStock
from app.models.stock_movement import StockMovement
from app.models.unserviceable_material import UnserviceableMaterial


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
    sm_query = db.query(
        func.coalesce(func.sum(StockMovement.quantity_in - StockMovement.quantity_out), 0)
    ).filter(
        StockMovement.item_id == item_id,
        StockMovement.is_active == True,
        StockMovement.transaction_source != TransactionSource.HISTORICAL,
    )

    if office_id is not None:
        sm_query = sm_query.filter(StockMovement.office_id == office_id)

    if financial_year_id is not None:
        sm_query = sm_query.filter(StockMovement.financial_year_id == financial_year_id)

    movement_balance = float(sm_query.scalar() or 0.0)

    has_opening_movement_query = db.query(StockMovement).filter(
        StockMovement.item_id == item_id,
        StockMovement.movement_type == MovementType.OPENING,
        StockMovement.is_active == True,
    )
    if office_id is not None:
        has_opening_movement_query = has_opening_movement_query.filter(StockMovement.office_id == office_id)
    if financial_year_id is not None:
        has_opening_movement_query = has_opening_movement_query.filter(StockMovement.financial_year_id == financial_year_id)

    has_opening_movement = has_opening_movement_query.first() is not None

    opening_balance = 0.0
    if not has_opening_movement:
        op_query = db.query(func.coalesce(func.sum(OpeningStock.quantity), 0)).filter(
            OpeningStock.item_id == item_id,
            OpeningStock.is_active == True,
        )
        if office_id is not None:
            op_query = op_query.filter(OpeningStock.office_id == office_id)
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

    if office_id is not None:
        un_query = un_query.filter(UnserviceableMaterial.office_id == office_id)

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

