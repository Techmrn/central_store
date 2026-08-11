import uuid
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.asset import Asset
from app.models.category import Category
from app.models.enums import AssetStatus, Category_Type, IndentStatus, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.models.opening_stock import OpeningStock
from app.models.section import Section
from app.schemas.issue import IssueCreate, IssueLineCreate
from app.crud.issue import create_issue, update_issue, delete_issue
from app.services.posting_service import post_issue
from app.services.stock_service import get_item_stock


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_full_partial_zero_issue_and_posting(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    sec = db_session.query(Section).filter(Section.office_id == office.id, Section.is_active == True).first()
    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Material Item A {uid}", code=f"TMAT-A-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    op = OpeningStock(financial_year_id=fy.id, office_id=office.id, item_id=item.id, quantity=100.0, unit_rate=10.0, total_value=1000.0)
    db_session.add(op)
    db_session.commit()

    stock_before = get_item_stock(db_session, item_id=item.id, office_id=office.id)
    assert stock_before == 100.0

    indent = Indent(
        indent_no=f"IND-{uid}-001",
        indent_date=date.today(),
        received_date=date.today(),
        financial_year_id=fy.id,
        office_id=office.id,
        section_id=sec.id if sec else None,
        status=IndentStatus.DRAFT,
    )
    indent.lines.append(IndentLine(item_id=item.id, requested_quantity=20.0, issued_quantity=15.0))
    db_session.add(indent)
    db_session.commit()
    db_session.refresh(indent)

    issue_in = IssueCreate(
        financial_year_id=fy.id,
        indent_id=indent.id,
        office_id=office.id,
        section_id=sec.id if sec else None,
        lines=[IssueLineCreate(item_id=item.id, unit_id=unit.id, quantity=15.0)]
    )
    issue = create_issue(db_session, issue_in=issue_in)
    assert issue.status == TransactionStatus.DRAFT
    assert len(issue.lines) == 1
    assert issue.lines[0].quantity == 15.0

    assert get_item_stock(db_session, item_id=item.id, office_id=office.id) == 100.0

    posted_issue = post_issue(db_session, issue_id=issue.id)
    assert posted_issue.status == TransactionStatus.POSTED
    assert indent.status == IndentStatus.CLOSED

    stock_after = get_item_stock(db_session, item_id=item.id, office_id=office.id)
    assert stock_after == 85.0

    with pytest.raises(ValueError, match="Cannot update a posted Issue document"):
        update_issue(db_session, issue_id=posted_issue.id, issue_in=IssueCreate(financial_year_id=fy.id, indent_id=indent.id, office_id=office.id, lines=[]))

    with pytest.raises(ValueError, match="Cannot delete a posted Issue document"):
        delete_issue(db_session, issue_id=posted_issue.id)


def test_insufficient_stock_rollback(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Material Item B {uid}", code=f"TMAT-B-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    op = OpeningStock(financial_year_id=fy.id, office_id=office.id, item_id=item.id, quantity=5.0, unit_rate=10.0, total_value=50.0)
    db_session.add(op)
    db_session.commit()

    indent = Indent(indent_no=f"IND-{uid}-002", indent_date=date.today(), received_date=date.today(), financial_year_id=fy.id, office_id=office.id, status=IndentStatus.DRAFT)
    indent.lines.append(IndentLine(item_id=item.id, requested_quantity=10.0, issued_quantity=10.0))
    db_session.add(indent)
    db_session.commit()

    issue = create_issue(db_session, issue_in=IssueCreate(financial_year_id=fy.id, indent_id=indent.id, office_id=office.id, lines=[IssueLineCreate(item_id=item.id, unit_id=unit.id, quantity=10.0)]))

    with pytest.raises(ValueError, match="Insufficient stock"):
        post_issue(db_session, issue_id=issue.id)

    db_session.refresh(issue)
    db_session.refresh(indent)
    assert issue.status == TransactionStatus.DRAFT
    assert indent.status == IndentStatus.DRAFT


def test_asset_issue_and_quantity_validation(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    dest_office = db_session.query(Office).filter(Office.id != office.id, Office.is_active == True).first() or office
    asset_cat = db_session.query(Category).filter(Category.type == Category_Type.ASSET, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test Desktop PC {uid}", code=f"TCOMP-{uid}", category_id=asset_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    asset1 = Asset(asset_no=f"TST-COMP-1-{uid}", item_id=item.id, office_id=office.id, status=AssetStatus.IN_STORE)
    asset2 = Asset(asset_no=f"TST-COMP-2-{uid}", item_id=item.id, office_id=office.id, status=AssetStatus.IN_STORE)
    db_session.add_all([asset1, asset2])
    db_session.commit()

    op = OpeningStock(financial_year_id=fy.id, office_id=office.id, item_id=item.id, quantity=2.0, unit_rate=5000.0, total_value=10000.0)
    db_session.add(op)
    db_session.commit()

    indent = Indent(indent_no=f"IND-{uid}-003", indent_date=date.today(), received_date=date.today(), financial_year_id=fy.id, office_id=office.id, status=IndentStatus.DRAFT)
    indent.lines.append(IndentLine(item_id=item.id, requested_quantity=2.0, issued_quantity=2.0))
    db_session.add(indent)
    db_session.commit()

    issue_invalid = create_issue(db_session, issue_in=IssueCreate(
        financial_year_id=fy.id, indent_id=indent.id, office_id=dest_office.id,
        lines=[IssueLineCreate(item_id=item.id, unit_id=unit.id, quantity=2.0, asset_ids=[asset1.id])]
    ))
    with pytest.raises(ValueError, match="Selected assets count"):
        post_issue(db_session, issue_id=issue_invalid.id)

    issue_valid = create_issue(db_session, issue_in=IssueCreate(
        financial_year_id=fy.id, indent_id=indent.id, office_id=dest_office.id,
        lines=[IssueLineCreate(item_id=item.id, unit_id=unit.id, quantity=2.0, asset_ids=[asset1.id, asset2.id])]
    ))
    posted = post_issue(db_session, issue_id=issue_valid.id)
    assert posted.status == TransactionStatus.POSTED

    db_session.refresh(asset1)
    db_session.refresh(asset2)
    assert asset1.status == AssetStatus.ISSUED
    assert asset2.status == AssetStatus.ISSUED
