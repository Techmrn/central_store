import uuid
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.asset import Asset
from app.models.category import Category
from app.models.enums import AssetStatus, Category_Type, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.schemas.stock_return import StockReturnCreate, StockReturnLineCreate
from app.crud.stock_return import create_return
from app.services.posting_service import post_return
from app.services.stock_service import get_item_stock


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_stock_return_material_and_asset(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    asset_cat = db_session.query(Category).filter(Category.type == Category_Type.ASSET, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Returnable Asset {uid}", code=f"TRASSET-{uid}", category_id=asset_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    asset = Asset(asset_no=f"TST-RET-ASSET-{uid}", item_id=item.id, office_id=office.id, status=AssetStatus.ISSUED)
    db_session.add(asset)
    db_session.commit()

    ret_in = StockReturnCreate(
        financial_year_id=fy.id,
        office_id=office.id,
        lines=[StockReturnLineCreate(item_id=item.id, unit_id=unit.id, quantity=1.0, asset_ids=[asset.id])]
    )
    ret_doc = create_return(db_session, return_in=ret_in)
    assert ret_doc.status == TransactionStatus.DRAFT

    posted_ret = post_return(db_session, return_id=ret_doc.id)
    assert posted_ret.status == TransactionStatus.POSTED

    db_session.refresh(asset)
    assert asset.status == AssetStatus.IN_STORE
    assert get_item_stock(db_session, item_id=item.id, office_id=office.id) == 1.0
