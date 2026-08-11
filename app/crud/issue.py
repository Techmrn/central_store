from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.enums import DestinationType, IndentStatus, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.issue import Issue, IssueLine, IssueLineAsset
from app.models.office import Office
from app.models.section import Section
from app.schemas.issue import IssueCreate, IssueUpdate
from app.services.document_number_service import generate_document_number


def _validate_office_and_section(
    db: Session,
    office_id: int,
    section_id: Optional[int] = None,
):
    office = db.query(Office).filter(Office.id == office_id, Office.is_active == True).first()
    if not office:
        raise ValueError("Office not found.")

    if section_id is not None:
        section = db.query(Section).filter(Section.id == section_id, Section.is_active == True).first()
        if not section:
            raise ValueError("Section not found.")
        if section.office_id != office_id:
            raise ValueError("The selected section does not belong to the specified office.")


def create_issue(
    db: Session,
    issue_in: IssueCreate,
    user_id: Optional[int] = None,
) -> Issue:
    # 1. Validate linked Indent
    indent = db.query(Indent).filter(Indent.id == issue_in.indent_id, Indent.is_active == True).first()
    if not indent:
        raise ValueError("Indent not found.")

    if indent.status == IndentStatus.CLOSED:
        raise ValueError("Cannot create an Issue for a closed Indent.")

    # 2. Validate office/section
    _validate_office_and_section(db, issue_in.office_id, issue_in.section_id)

    # 3. Document number
    if issue_in.issue_no:
        clean_no = issue_in.issue_no.strip()
        existing = db.query(Issue).filter(func.lower(Issue.issue_no) == clean_no.lower()).first()
        if existing:
            raise ValueError(f"Issue number '{clean_no}' already exists.")
        issue_no = clean_no
    else:
        issue_no = generate_document_number(
            db=db,
            model_class=Issue,
            number_field_name="issue_no",
            prefix="ISS",
            financial_year_id=issue_in.financial_year_id,
        )

    # 4. Create Issue Header
    issue_date = issue_in.issue_date or date.today()

    db_issue = Issue(
        issue_no=issue_no,
        issue_date=issue_date,
        financial_year_id=issue_in.financial_year_id,
        indent_id=issue_in.indent_id,
        office_id=issue_in.office_id,
        section_id=issue_in.section_id,
        destination_type=issue_in.destination_type or DestinationType.INTERNAL,
        status=TransactionStatus.DRAFT,
        reference_no=issue_in.reference_no.strip() if issue_in.reference_no else None,
        remarks=issue_in.remarks.strip() if issue_in.remarks else None,
        created_by_id=user_id,
    )

    # 5. Create Issue Lines
    indent_lines_by_item = {l.item_id: l for l in indent.lines if l.is_active}

    for line_in in issue_in.lines:
        indent_line = indent_lines_by_item.get(line_in.item_id)
        if not indent_line:
            raise ValueError(f"Item ID {line_in.item_id} is not present in the reference Indent.")

        # Check: Issue quantity <= Indent issued/requested quantity
        max_allowed = indent_line.requested_quantity
        if line_in.quantity > max_allowed:
            raise ValueError(
                f"Issue quantity ({line_in.quantity}) cannot exceed requested quantity ({max_allowed}) for item ID {line_in.item_id}."
            )

        db_line = IssueLine(
            item_id=line_in.item_id,
            unit_id=line_in.unit_id,
            quantity=line_in.quantity,
            remarks=line_in.remarks.strip() if line_in.remarks else None,
        )

        if line_in.asset_ids:
            for aid in line_in.asset_ids:
                db_line.assets.append(IssueLineAsset(asset_id=aid))

        db_issue.lines.append(db_line)

    db.add(db_issue)
    try:
        db.commit()
        db.refresh(db_issue)
        return db_issue
    except Exception:
        db.rollback()
        raise


def get_issue_by_id(db: Session, issue_id: int) -> Optional[Issue]:
    return db.query(Issue).filter(Issue.id == issue_id, Issue.is_active == True).first()


def get_all_issues(
    db: Session,
    search: str = "",
    issue_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[TransactionStatus] = None,
    page: int = 1,
):
    query = (
        db.query(Issue)
        .join(Office, Issue.office_id == Office.id)
        .join(FinancialYear, Issue.financial_year_id == FinancialYear.id)
        .filter(
            Issue.is_active == True,
            Office.is_active == True,
            FinancialYear.is_active == True,
        )
    )

    if issue_no:
        query = query.filter(func.lower(Issue.issue_no) == issue_no.strip().lower())

    if financial_year_id is not None:
        query = query.filter(Issue.financial_year_id == financial_year_id)

    if office_id is not None:
        query = query.filter(Issue.office_id == office_id)

    if section_id is not None:
        query = query.filter(Issue.section_id == section_id)

    if status is not None:
        query = query.filter(Issue.status == status)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                Issue.issue_no.ilike(f"%{clean}%"),
                Issue.reference_no.ilike(f"%{clean}%"),
                Office.name.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(Issue.id.desc())
    return get_pagination_result(query, page)


def update_issue(
    db: Session,
    issue_id: int,
    issue_in: IssueUpdate,
) -> Issue:
    db_issue = get_issue_by_id(db, issue_id)
    if not db_issue:
        raise ValueError("Issue document not found.")

    if db_issue.status == TransactionStatus.POSTED:
        raise ValueError("Cannot update a posted Issue document.")

    if issue_in.office_id is not None or issue_in.section_id is not None:
        target_off = issue_in.office_id if issue_in.office_id is not None else db_issue.office_id
        target_sec = issue_in.section_id if issue_in.section_id is not None else db_issue.section_id
        _validate_office_and_section(db, target_off, target_sec)
        db_issue.office_id = target_off
        db_issue.section_id = target_sec

    if issue_in.destination_type is not None:
        db_issue.destination_type = issue_in.destination_type

    if issue_in.issue_date is not None:
        db_issue.issue_date = issue_in.issue_date

    if issue_in.reference_no is not None:
        db_issue.reference_no = issue_in.reference_no.strip() if issue_in.reference_no else None

    if issue_in.remarks is not None:
        db_issue.remarks = issue_in.remarks.strip() if issue_in.remarks else None

    if issue_in.lines is not None:
        db_issue.lines.clear()
        indent = db_issue.indent
        indent_lines_by_item = {l.item_id: l for l in indent.lines if l.is_active}

        for line_in in issue_in.lines:
            indent_line = indent_lines_by_item.get(line_in.item_id)
            if not indent_line:
                raise ValueError(f"Item ID {line_in.item_id} is not present in reference Indent.")

            if line_in.quantity > indent_line.requested_quantity:
                raise ValueError(
                    f"Issue quantity ({line_in.quantity}) cannot exceed requested quantity ({indent_line.requested_quantity}) for item ID {line_in.item_id}."
                )

            db_line = IssueLine(
                item_id=line_in.item_id,
                unit_id=line_in.unit_id,
                quantity=line_in.quantity,
                remarks=line_in.remarks.strip() if line_in.remarks else None,
            )
            if line_in.asset_ids:
                for aid in line_in.asset_ids:
                    db_line.assets.append(IssueLineAsset(asset_id=aid))

            db_issue.lines.append(db_line)

    try:
        db.commit()
        db.refresh(db_issue)
        return db_issue
    except Exception:
        db.rollback()
        raise


def delete_issue(db: Session, issue_id: int) -> Optional[Issue]:
    db_issue = get_issue_by_id(db, issue_id)
    if not db_issue:
        return None

    if db_issue.status == TransactionStatus.POSTED:
        raise ValueError("Cannot delete a posted Issue document.")

    db_issue.is_active = False
    for line in db_issue.lines:
        line.is_active = False

    try:
        db.commit()
        return db_issue
    except Exception:
        db.rollback()
        raise
