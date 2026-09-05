from decimal import Decimal

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import Category_Type
from app.models.financial_year import FinancialYear
from app.models.office import Office
from app.models.item import Item
from app.models.opening_stock import OpeningStock
from app.services.scope_service import get_stock_office_id
from app.schemas.opening_stock import (
    OpeningStockCreate,
    OpeningStockUpdate,
)


def create_opening_stock(
    db: Session,
    opening_stock: OpeningStockCreate,
):
    financial_year = (
        db.query(FinancialYear)
        .filter(
            FinancialYear.id == opening_stock.financial_year_id,
            FinancialYear.is_active == True,
        )
        .first()
    )

    if financial_year is None:
        raise ValueError("Financial Year not found.")

    office = (
        db.query(Office)
        .filter(
            Office.id == opening_stock.office_id,
            Office.is_active == True,
        )
        .first()
    )

    if office is None:
        raise ValueError("Office not found.")

    # Opening Stock belongs to the stock-owning store, not necessarily the
    # administrative office selected by the user. Directorate and GCP share
    # one canonical Central Store.
    stock_office_id = get_stock_office_id(db, opening_stock.office_id)

    item = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.id == opening_stock.item_id,
            Item.is_active == True,
            Category.is_active == True,
        )
        .first()
    )

    if item is None:
        raise ValueError("Item not found.")

    if item.category.type != Category_Type.MATERIAL:
        raise ValueError(
            "Opening stock can only be created for Material items. "
            "Asset items must be registered through the Asset Register."
        )

    duplicate = (
        db.query(OpeningStock)
        .filter(
            OpeningStock.is_active == True,
            and_(
                OpeningStock.financial_year_id == opening_stock.financial_year_id,
                OpeningStock.office_id == stock_office_id,
                OpeningStock.item_id == opening_stock.item_id,
            ),
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Opening stock already exists for this Financial Year, Office and Item."
        )

    if opening_stock.quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    if opening_stock.unit_rate < 0:
        raise ValueError("Unit rate cannot be negative.")

    try:
        db_opening_stock = OpeningStock(
            financial_year_id=opening_stock.financial_year_id,
            office_id=stock_office_id,
            item_id=opening_stock.item_id,
            quantity=opening_stock.quantity,
            unit_rate=opening_stock.unit_rate,
            total_value=(
                Decimal(opening_stock.quantity)
                * Decimal(opening_stock.unit_rate)
            ),
            remarks=opening_stock.remarks.strip()
            if opening_stock.remarks
            else None,
        )

        db.add(db_opening_stock)
        db.commit()
        db.refresh(db_opening_stock)

        return db_opening_stock

    except Exception:
        db.rollback()
        raise


def get_all_opening_stocks(db: Session):
    return (
        db.query(OpeningStock)
        .filter(OpeningStock.is_active == True)
        .order_by(
            OpeningStock.financial_year_id,
            OpeningStock.office_id,
            OpeningStock.item_id,
        )
        .all()
    )


def get_opening_stock_by_id(
    db: Session,
    opening_stock_id: int,
):
    return (
        db.query(OpeningStock)
        .filter(
            OpeningStock.id == opening_stock_id,
            OpeningStock.is_active == True,
        )
        .first()
    )


def update_opening_stock(
    db: Session,
    opening_stock_id: int,
    opening_stock: OpeningStockUpdate,
):
    db_opening_stock = (
        db.query(OpeningStock)
        .filter(
            OpeningStock.id == opening_stock_id,
            OpeningStock.is_active == True,
        )
        .first()
    )

    if db_opening_stock is None:
        return None

    data = opening_stock.model_dump(exclude_unset=True)

    financial_year_id = data.get(
        "financial_year_id",
        db_opening_stock.financial_year_id,
    )

    office_id = data.get(
        "office_id",
        db_opening_stock.office_id,
    )
    office = (
        db.query(Office)
        .filter(Office.id == office_id, Office.is_active == True)
        .first()
    )
    if office is None:
        raise ValueError("Office not found.")
    office_id = get_stock_office_id(db, office_id)

    item_id = data.get(
        "item_id",
        db_opening_stock.item_id,
    )

    # Validate item is MATERIAL if item_id is being changed
    if "item_id" in data:
        check_item = (
            db.query(Item)
            .join(Category, Item.category_id == Category.id)
            .filter(
                Item.id == item_id,
                Item.is_active == True,
                Category.is_active == True,
            )
            .first()
        )
        if check_item is None:
            raise ValueError("Item not found.")
        if check_item.category.type != Category_Type.MATERIAL:
            raise ValueError(
                "Opening stock can only be updated for Material items. "
                "Asset items must be registered through the Asset Register."
            )

    duplicate = (
        db.query(OpeningStock)
        .filter(
            OpeningStock.is_active == True,
            OpeningStock.id != opening_stock_id,
            OpeningStock.financial_year_id == financial_year_id,
            OpeningStock.office_id == office_id,
            OpeningStock.item_id == item_id,
        )
        .first()
    )

    if duplicate:
        raise ValueError(
            "Opening stock already exists for this Financial Year, Office and Item."
        )

    # OpeningStock is a stock-owner record, so always keep its office on the
    # canonical stock-owning store even when the caller did not change office.
    db_opening_stock.office_id = office_id

    for key, value in data.items():
        if key == "office_id":
            value = office_id
        elif key == "remarks" and value is not None:
            value = value.strip()

        setattr(db_opening_stock, key, value)

    db_opening_stock.total_value = (
        Decimal(db_opening_stock.quantity)
        * Decimal(db_opening_stock.unit_rate)
    )

    try:
        db.commit()
        db.refresh(db_opening_stock)

        return db_opening_stock

    except Exception:
        db.rollback()
        raise


def delete_opening_stock(
    db: Session,
    opening_stock_id: int,
):
    db_opening_stock = (
        db.query(OpeningStock)
        .filter(
            OpeningStock.id == opening_stock_id,
            OpeningStock.is_active == True,
        )
        .first()
    )

    if db_opening_stock is None:
        return None

    try:
        db_opening_stock.is_active = False

        db.commit()
        db.refresh(db_opening_stock)

        return db_opening_stock

    except Exception:
        db.rollback()
        raise