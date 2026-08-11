import uuid
import pytest
from datetime import date
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.category import Category
from app.models.enums import Category_Type, DestinationType, IndentStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.unit import Unit
from app.models.office import Office
from app.schemas.issue import IssueCreate, IssueLineCreate
from app.crud.issue import create_issue
from app.schemas.outward_pass import OutwardPassCreate
from app.crud.outward_pass import create_outward_pass, get_outward_pass_by_issue_id


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_outward_pass_creation_linked_to_external_issue(db_session: Session):
    uid = uuid.uuid4().hex[:6]
    fy = db_session.query(FinancialYear).filter(FinancialYear.is_active == True).first()
    office = db_session.query(Office).filter(Office.is_active == True).first()
    mat_cat = db_session.query(Category).filter(Category.type == Category_Type.MATERIAL, Category.is_active == True).first()
    unit = db_session.query(Unit).filter(Unit.is_active == True).first()

    item = Item(name=f"Test External Material {uid}", code=f"TEXT-{uid}", category_id=mat_cat.id, unit_id=unit.id)
    db_session.add(item)
    db_session.commit()

    indent = Indent(indent_no=f"IND-PASS-{uid}", indent_date=date.today(), received_date=date.today(), financial_year_id=fy.id, office_id=office.id, status=IndentStatus.DRAFT)
    indent.lines.append(IndentLine(item_id=item.id, requested_quantity=5.0))
    db_session.add(indent)
    db_session.commit()

    issue_in = IssueCreate(
        financial_year_id=fy.id,
        indent_id=indent.id,
        office_id=office.id,
        destination_type=DestinationType.EXTERNAL,
        lines=[IssueLineCreate(item_id=item.id, unit_id=unit.id, quantity=5.0)]
    )
    issue = create_issue(db_session, issue_in=issue_in)

    pass_in = OutwardPassCreate(
        issue_id=issue.id,
        purpose="Transporting equipment to external press unit",
        recipient_name="John Driver",
        destination="External Press Unit #4",
        vehicle_no="KA-01-AB-1234",
    )
    op = create_outward_pass(db_session, pass_in=pass_in)
    assert op.issue_id == issue.id
    assert op.pass_no.startswith("OP-")

    op_fetched = get_outward_pass_by_issue_id(db_session, issue_id=issue.id)
    assert op_fetched.id == op.id
