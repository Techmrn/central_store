import uuid
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.category import Category
from app.models.enums import Category_Type, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.models.opening_stock import OpeningStock
from app.schemas.stock_transfer import StockTransferCreate, StockTransferLineCreate
from app.crud.stock_transfer import create_transfer
from app.services.posting_service import post_transfer
from app.services.stock_service import get_item_stock


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_stock_transfer_posting(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    offices = db_session.query(Office).filter(Office.is_active == True).all()
    if len(offices) < 2:
        off1 = offices[0]
        off2 = Office(name=f"Test Branch Office B {uid}", code=f"TBOB-{uid}")
        db_session.add(off2)
        db_session.commit()
    else:
        off1, off2 = offices[0], offices[1]

    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Transfer Item {uid}", code=f"TTRN-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    op = OpeningStock(financial_year_id=fy.id, office_id=off1.id, item_id=item.id, quantity=50.0, unit_rate=10.0, total_value=500.0)
    db_session.add(op)
    db_session.commit()

    assert get_item_stock(db_session, item_id=item.id, office_id=off1.id) == 50.0
    assert get_item_stock(db_session, item_id=item.id, office_id=off2.id) == 0.0

    trn_in = StockTransferCreate(
        financial_year_id=fy.id,
        from_office_id=off1.id,
        to_office_id=off2.id,
        lines=[StockTransferLineCreate(item_id=item.id, unit_id=unit.id, quantity=20.0)]
    )
    trn_doc = create_transfer(db_session, transfer_in=trn_in)
    assert trn_doc.status == TransactionStatus.DRAFT

    posted_trn = post_transfer(db_session, transfer_id=trn_doc.id)
    assert posted_trn.status == TransactionStatus.POSTED

    assert get_item_stock(db_session, item_id=item.id, office_id=off1.id) == 30.0
    assert get_item_stock(db_session, item_id=item.id, office_id=off2.id) == 20.0
