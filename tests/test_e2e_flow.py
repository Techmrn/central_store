import uuid
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.asset import Asset
from app.models.category import Category
from app.models.enums import AssetMovementType, AssetStatus, Category_Type, DestinationType, IndentStatus, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.models.opening_stock import OpeningStock
from app.models.section import Section
from app.schemas.issue import IssueCreate, IssueLineCreate
from app.crud.issue import create_issue
from app.schemas.outward_pass import OutwardPassCreate
from app.crud.outward_pass import create_outward_pass
from app.services.posting_service import post_issue
from app.services.stock_service import get_item_stock
from app.crud.stock import get_distribution_register, get_asset_register_report, get_computer_register_report


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_complete_end_to_end_flow(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    store_office = db_session.query(Office).filter(Office.is_active == True).first()
    dest_office = db_session.query(Office).filter(Office.id != store_office.id, Office.is_active == True).first() or store_office
    dest_section = db_session.query(Section).filter(Section.office_id == dest_office.id, Section.is_active == True).first()

    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    asset_cat = db_session.query(Category).filter(Category.type == Category_Type.ASSET, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    paper_item = Item(name=f"E2E A4 Paper {uid}", code=f"E2E-PAPER-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    comp_item = Item(name=f"E2E Desktop Computer {uid}", code=f"E2E-COMP-{uid}", category_id=asset_cat.id, unit_id=unit.id)
    db_session.add_all([paper_item, comp_item])
    db_session.commit()

    op1 = OpeningStock(financial_year_id=fy.id, office_id=store_office.id, item_id=paper_item.id, quantity=100.0, unit_rate=200.0, total_value=20000.0)
    op2 = OpeningStock(financial_year_id=fy.id, office_id=store_office.id, item_id=comp_item.id, quantity=2.0, unit_rate=45000.0, total_value=90000.0)
    db_session.add_all([op1, op2])
    db_session.commit()

    comp_asset1 = Asset(asset_no=f"E2E-PC-1-{uid}", item_id=comp_item.id, office_id=store_office.id, status=AssetStatus.IN_STORE)
    comp_asset2 = Asset(asset_no=f"E2E-PC-2-{uid}", item_id=comp_item.id, office_id=store_office.id, status=AssetStatus.IN_STORE)
    db_session.add_all([comp_asset1, comp_asset2])
    db_session.commit()

    assert get_item_stock(db_session, item_id=paper_item.id, office_id=store_office.id) == 100.0
    assert get_item_stock(db_session, item_id=comp_item.id, office_id=store_office.id) == 2.0

    indent = Indent(
        indent_no=f"IND-E2E-{uid}",
        indent_date=date(2026, 9, 1),
        received_date=date(2026, 9, 1),
        financial_year_id=fy.id,
        office_id=store_office.id,
        status=IndentStatus.DRAFT,
    )
    indent.lines.append(IndentLine(item_id=paper_item.id, requested_quantity=20.0, issued_quantity=15.0))
    indent.lines.append(IndentLine(item_id=comp_item.id, requested_quantity=1.0, issued_quantity=1.0))
    db_session.add(indent)
    db_session.commit()

    issue_in = IssueCreate(
        financial_year_id=fy.id,
        indent_id=indent.id,
        office_id=dest_office.id,
        section_id=dest_section.id if dest_section else None,
        destination_type=DestinationType.EXTERNAL,
        lines=[
            IssueLineCreate(item_id=paper_item.id, unit_id=unit.id, quantity=15.0),
            IssueLineCreate(item_id=comp_item.id, unit_id=unit.id, quantity=1.0, asset_ids=[comp_asset1.id]),
        ]
    )
    issue = create_issue(db_session, issue_in=issue_in)
    assert issue.status == TransactionStatus.DRAFT

    pass_in = OutwardPassCreate(
        issue_id=issue.id,
        purpose="Delivery to Branch Office",
        recipient_name="Store Driver Rakesh",
        destination=dest_office.name,
        vehicle_no="KA-02-CD-5678",
    )
    op = create_outward_pass(db_session, pass_in=pass_in)
    assert op.issue_id == issue.id

    posted_issue = post_issue(db_session, issue_id=issue.id)
    assert posted_issue.status == TransactionStatus.POSTED

    db_session.refresh(indent)
    assert indent.status == IndentStatus.CLOSED

    assert get_item_stock(db_session, item_id=paper_item.id, office_id=store_office.id) == 85.0
    assert get_item_stock(db_session, item_id=comp_item.id, office_id=store_office.id) == 1.0

    db_session.refresh(comp_asset1)
    assert comp_asset1.status == AssetStatus.ISSUED
    assert comp_asset1.office_id == dest_office.id
    assert len(comp_asset1.movements) > 0
    assert comp_asset1.movements[0].movement_type == AssetMovementType.ISSUE

    dist_report = get_distribution_register(db_session, financial_year_id=fy.id, office_id=dest_office.id)
    dist_items = dist_report["items"]
    assert len(dist_items) >= 2
    issue_nos = [di.issue_no for di in dist_items]
    assert posted_issue.issue_no in issue_nos

    comp_report = get_computer_register_report(db_session, office_id=dest_office.id)
    comp_assets = [c.asset_no for c in comp_report["items"]]
    assert comp_asset1.asset_no in comp_assets
