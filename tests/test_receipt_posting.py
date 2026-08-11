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
from app.schemas.receipt import ReceiptCreate, ReceiptLineCreate
from app.crud.receipt import create_receipt
from app.services.posting_service import post_receipt
from app.services.stock_service import get_item_stock


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_receipt_creation_posting_and_stock_increase(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Receipt Item {uid}", code=f"TREC-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    initial_stock = get_item_stock(db_session, item_id=item.id, office_id=office.id)
    assert initial_stock == 0.0

    rec_in = ReceiptCreate(
        financial_year_id=fy.id,
        office_id=office.id,
        supplier_name="ABC Suppliers Ltd",
        reference_no=f"INV-{uid}",
        lines=[ReceiptLineCreate(item_id=item.id, unit_id=unit.id, quantity=50.0, unit_price=25.0)]
    )
    receipt = create_receipt(db_session, receipt_in=rec_in)
    assert receipt.status == TransactionStatus.DRAFT

    assert get_item_stock(db_session, item_id=item.id, office_id=office.id) == 0.0

    posted_receipt = post_receipt(db_session, receipt_id=receipt.id)
    assert posted_receipt.status == TransactionStatus.POSTED

    final_stock = get_item_stock(db_session, item_id=item.id, office_id=office.id)
    assert final_stock == 50.0
