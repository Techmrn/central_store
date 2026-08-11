from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.issue import Issue
from app.models.outward_pass import OutwardPass
from app.schemas.outward_pass import OutwardPassCreate
from app.services.document_number_service import generate_document_number


def create_outward_pass(
    db: Session,
    pass_in: OutwardPassCreate,
    user_id: Optional[int] = None,
) -> OutwardPass:
    issue = db.query(Issue).filter(Issue.id == pass_in.issue_id, Issue.is_active == True).first()
    if not issue:
        raise ValueError("Linked Issue document not found.")

    existing_pass = db.query(OutwardPass).filter(OutwardPass.issue_id == pass_in.issue_id, OutwardPass.is_active == True).first()
    if existing_pass:
        raise ValueError("An Outward Pass already exists for this Issue.")

    if pass_in.pass_no:
        clean_no = pass_in.pass_no.strip()
        existing = db.query(OutwardPass).filter(func.lower(OutwardPass.pass_no) == clean_no.lower()).first()
        if existing:
            raise ValueError(f"Outward pass number '{clean_no}' already exists.")
        pass_no = clean_no
    else:
        pass_no = generate_document_number(
            db=db,
            model_class=OutwardPass,
            number_field_name="pass_no",
            prefix="OP",
            financial_year_id=issue.financial_year_id,
        )

    pass_date = pass_in.pass_date or date.today()

    db_pass = OutwardPass(
        pass_no=pass_no,
        pass_date=pass_date,
        issue_id=pass_in.issue_id,
        purpose=pass_in.purpose.strip(),
        recipient_name=pass_in.recipient_name.strip(),
        destination=pass_in.destination.strip(),
        vehicle_no=pass_in.vehicle_no.strip() if pass_in.vehicle_no else None,
        remarks=pass_in.remarks.strip() if pass_in.remarks else None,
        created_by_id=user_id,
    )

    db.add(db_pass)
    try:
        db.commit()
        db.refresh(db_pass)
        return db_pass
    except Exception:
        db.rollback()
        raise


def get_outward_pass_by_id(db: Session, pass_id: int) -> Optional[OutwardPass]:
    return db.query(OutwardPass).filter(OutwardPass.id == pass_id, OutwardPass.is_active == True).first()


def get_outward_pass_by_issue_id(db: Session, issue_id: int) -> Optional[OutwardPass]:
    return db.query(OutwardPass).filter(OutwardPass.issue_id == issue_id, OutwardPass.is_active == True).first()


def get_all_outward_passes(
    db: Session,
    search: str = "",
    pass_no: Optional[str] = None,
    issue_id: Optional[int] = None,
    page: int = 1,
):
    query = db.query(OutwardPass).filter(OutwardPass.is_active == True)

    if pass_no:
        query = query.filter(func.lower(OutwardPass.pass_no) == pass_no.strip().lower())

    if issue_id is not None:
        query = query.filter(OutwardPass.issue_id == issue_id)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                OutwardPass.pass_no.ilike(f"%{clean}%"),
                OutwardPass.recipient_name.ilike(f"%{clean}%"),
                OutwardPass.destination.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(OutwardPass.id.desc())
    return get_pagination_result(query, page)
