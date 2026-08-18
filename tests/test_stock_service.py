import uuid
import pytest
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.crud.category import create_category
from app.crud.financial_year import create_financial_year
from app.crud.item import create_item
from app.crud.office import create_office
from app.crud.opening_stock import create_opening_stock
from app.crud.unit import create_unit
from app.models.enums import Category_Type, MovementType, TransactionSource
from app.models.office import OfficeType
from app.models.stock_movement import StockMovement
from app.schemas.category import CategoryCreate
from app.schemas.financial_year import FinancialYearCreate
from app.schemas.item import ItemCreate
from app.schemas.office import OfficeCreate
from app.schemas.opening_stock import OpeningStockCreate
from app.schemas.unit import UnitCreate
from app.services.stock_service import (
    get_item_stock,
    get_item_unserviceable_stock,
    get_item_usable_stock,
    validate_stock_availability,
)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_or_create_test_fy(db: Session, start_year: int, is_current: bool = False, is_closed: bool = False):
    year_name = f"{start_year}-{str(start_year + 1)[-2:]}"
    from app.models.financial_year import FinancialYear
    fy = db.query(FinancialYear).filter(FinancialYear.year_name == year_name).first()
    if not fy:
        fy = FinancialYear(
            year_name=year_name,
            start_date=date(start_year, 4, 1),
            end_date=date(start_year + 1, 3, 31),
            is_current=is_current,
            is_closed=is_closed,
        )
        db.add(fy)
        db.commit()
        db.refresh(fy)
    else:
        fy.is_closed = is_closed
        if is_current:
            fy.is_current = True
        db.commit()
        db.refresh(fy)
    return fy


@pytest.fixture
def stock_fixture(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    office = create_office(db_session, OfficeCreate(name=f"Stock Test Office {uid}", code=f"STO{uid}", office_type=OfficeType.GCP))
    unit = create_unit(db_session, UnitCreate(name=f"Units {uid}", symbol=f"U{uid}"))
    cat = create_category(db_session, CategoryCreate(name=f"General {uid}", code=f"GEN{uid}", type=Category_Type.MATERIAL))
    item = create_item(db_session, ItemCreate(name=f"Stock Item {uid}", code=f"SI-{uid}", category_id=cat.id, unit_id=unit.id))

    fy1 = get_or_create_test_fy(db_session, 2038, is_current=False, is_closed=False)
    fy2 = get_or_create_test_fy(db_session, 2039, is_current=True, is_closed=False)

    return {
        "office": office,
        "unit": unit,
        "cat": cat,
        "item": item,
        "fy1": fy1,
        "fy2": fy2,
    }


def test_stock_service_opening_movement_fy_isolation(db_session: Session, stock_fixture):
    f = stock_fixture
    item = f["item"]
    office = f["office"]
    fy1 = f["fy1"]
    fy2 = f["fy2"]

    # In FY1, create an explicit OPENING StockMovement
    sm_fy1 = StockMovement(
        financial_year_id=fy1.id,
        item_id=item.id,
        office_id=office.id,
        movement_type=MovementType.OPENING,
        transaction_source=TransactionSource.OPENING,
        quantity_in=100.0,
        quantity_out=0.0,
        reference_type="OPENING_BALANCE",
        reference_id=1,
    )
    db_session.add(sm_fy1)

    # In FY2, create an OpeningStock record (no StockMovement yet)
    create_opening_stock(
        db_session,
        OpeningStockCreate(
            financial_year_id=fy2.id,
            item_id=item.id,
            office_id=office.id,
            quantity=Decimal("50.0"),
            unit_rate=Decimal("10.0"),
        ),
    )
    db_session.commit()

    # Verify that FY1 opening movement does NOT suppress FY2 OpeningStock fallback
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy1.id) == 100.0
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy2.id) == 50.0
    assert get_item_usable_stock(db_session, item_id=item.id, office_id=office.id, financial_year_id=fy2.id) == 50.0
    assert validate_stock_availability(db_session, item_id=item.id, office_id=office.id, required_qty=50.0, financial_year_id=fy2.id) is True
