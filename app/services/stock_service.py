from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import MovementType, TransactionSource
from app.models.opening_stock import OpeningStock
from app.models.stock_movement import StockMovement


def get_item_stock(
    db: Session,
    item_id: int,
    office_id: Optional[int] = None,
) -> float:
    """
    Calculate total current available stock for an Item.
    Current Stock = Opening Stock + Receipts + Returns + Transfer In + Adjustment In - Issues - Transfer Out - Adjustment Out
    Excludes historical audit transactions (transaction_source == HISTORICAL).
    """
    # 1. Sum stock movements
    sm_query = db.query(
        func.coalesce(func.sum(StockMovement.quantity_in - StockMovement.quantity_out), 0)
    ).filter(
        StockMovement.item_id == item_id,
        StockMovement.is_active == True,
        StockMovement.transaction_source != TransactionSource.HISTORICAL,
    )

    if office_id is not None:
        sm_query = sm_query.filter(StockMovement.office_id == office_id)

    movement_balance = float(sm_query.scalar() or 0.0)

    # 2. Check if OPENING movement exists in stock_movements
    has_opening_movement_query = db.query(StockMovement).filter(
        StockMovement.item_id == item_id,
        StockMovement.movement_type == MovementType.OPENING,
        StockMovement.is_active == True,
    )
    if office_id is not None:
        has_opening_movement_query = has_opening_movement_query.filter(StockMovement.office_id == office_id)

    has_opening_movement = has_opening_movement_query.first() is not None

    # If opening stock movement isn't explicitly in StockMovement table, add from OpeningStock table
    opening_balance = 0.0
    if not has_opening_movement:
        op_query = db.query(func.coalesce(func.sum(OpeningStock.quantity), 0)).filter(
            OpeningStock.item_id == item_id,
            OpeningStock.is_active == True,
        )
        if office_id is not None:
            op_query = op_query.filter(OpeningStock.office_id == office_id)
        opening_balance = float(op_query.scalar() or 0.0)

    total_stock = opening_balance + movement_balance
    return round(total_stock, 2)


def validate_stock_availability(
    db: Session,
    item_id: int,
    office_id: int,
    required_qty: float,
) -> bool:
    """
    Check if available stock is >= required_qty.
    Raises ValueError if stock is insufficient.
    """
    current = get_item_stock(db, item_id=item_id, office_id=office_id)
    if current < required_qty:
        raise ValueError(
            f"Insufficient stock for item ID {item_id}. Available: {current}, Requested: {required_qty}."
        )
    return True
