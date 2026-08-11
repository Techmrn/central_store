from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.item import Item
from app.models.office import Office
from app.models.receipt import Receipt, ReceiptLine
from app.models.section import Section
from app.schemas.receipt import ReceiptCreate, ReceiptUpdate
from app.services.document_number_service import generate_document_number


def create_receipt(
    db: Session,
    receipt_in: ReceiptCreate,
    user_id: Optional[int] = None,
) -> Receipt:
    office = db.query(Office).filter(Office.id == receipt_in.office_id, Office.is_active == True).first()
    if not office:
        raise ValueError("Office not found.")

    if receipt_in.section_id is not None:
        sec = db.query(Section).filter(Section.id == receipt_in.section_id, Section.is_active == True).first()
        if not sec or sec.office_id != receipt_in.office_id:
            raise ValueError("Invalid section for specified office.")

    if receipt_in.receipt_no:
        clean_no = receipt_in.receipt_no.strip()
        existing = db.query(Receipt).filter(func.lower(Receipt.receipt_no) == clean_no.lower()).first()
        if existing:
            raise ValueError(f"Receipt number '{clean_no}' already exists.")
        receipt_no = clean_no
    else:
        receipt_no = generate_document_number(
            db=db,
            model_class=Receipt,
            number_field_name="receipt_no",
            prefix="REC",
            financial_year_id=receipt_in.financial_year_id,
        )

    receipt_date = receipt_in.receipt_date or date.today()

    db_receipt = Receipt(
        receipt_no=receipt_no,
        receipt_date=receipt_date,
        financial_year_id=receipt_in.financial_year_id,
        office_id=receipt_in.office_id,
        section_id=receipt_in.section_id,
        supplier_name=receipt_in.supplier_name.strip() if receipt_in.supplier_name else None,
        reference_no=receipt_in.reference_no.strip() if receipt_in.reference_no else None,
        status=TransactionStatus.DRAFT,
        remarks=receipt_in.remarks.strip() if receipt_in.remarks else None,
        created_by_id=user_id,
    )

    for line_in in receipt_in.lines:
        item = db.query(Item).filter(Item.id == line_in.item_id, Item.is_active == True).first()
        if not item:
            raise ValueError(f"Item ID {line_in.item_id} not found.")

        db_receipt.lines.append(
            ReceiptLine(
                item_id=line_in.item_id,
                unit_id=line_in.unit_id,
                quantity=line_in.quantity,
                unit_price=line_in.unit_price,
                remarks=line_in.remarks.strip() if line_in.remarks else None,
            )
        )

    db.add(db_receipt)
    try:
        db.commit()
        db.refresh(db_receipt)
        return db_receipt
    except Exception:
        db.rollback()
        raise


def get_receipt_by_id(db: Session, receipt_id: int) -> Optional[Receipt]:
    return db.query(Receipt).filter(Receipt.id == receipt_id, Receipt.is_active == True).first()


def get_all_receipts(
    db: Session,
    search: str = "",
    receipt_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    status: Optional[TransactionStatus] = None,
    page: int = 1,
):
    query = (
        db.query(Receipt)
        .join(Office, Receipt.office_id == Office.id)
        .join(FinancialYear, Receipt.financial_year_id == FinancialYear.id)
        .filter(
            Receipt.is_active == True,
            Office.is_active == True,
            FinancialYear.is_active == True,
        )
    )

    if receipt_no:
        query = query.filter(func.lower(Receipt.receipt_no) == receipt_no.strip().lower())

    if financial_year_id is not None:
        query = query.filter(Receipt.financial_year_id == financial_year_id)

    if office_id is not None:
        query = query.filter(Receipt.office_id == office_id)

    if status is not None:
        query = query.filter(Receipt.status == status)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                Receipt.receipt_no.ilike(f"%{clean}%"),
                Receipt.supplier_name.ilike(f"%{clean}%"),
                Receipt.reference_no.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(Receipt.id.desc())
    return get_pagination_result(query, page)


def update_receipt(
    db: Session,
    receipt_id: int,
    receipt_in: ReceiptUpdate,
) -> Receipt:
    db_receipt = get_receipt_by_id(db, receipt_id)
    if not db_receipt:
        raise ValueError("Receipt document not found.")

    if db_receipt.status == TransactionStatus.POSTED:
        raise ValueError("Cannot update a posted Receipt document.")

    if receipt_in.supplier_name is not None:
        db_receipt.supplier_name = receipt_in.supplier_name.strip() if receipt_in.supplier_name else None

    if receipt_in.reference_no is not None:
        db_receipt.reference_no = receipt_in.reference_no.strip() if receipt_in.reference_no else None

    if receipt_in.remarks is not None:
        db_receipt.remarks = receipt_in.remarks.strip() if receipt_in.remarks else None

    if receipt_in.lines is not None:
        db_receipt.lines.clear()
        for line_in in receipt_in.lines:
            db_receipt.lines.append(
                ReceiptLine(
                    item_id=line_in.item_id,
                    unit_id=line_in.unit_id,
                    quantity=line_in.quantity,
                    unit_price=line_in.unit_price,
                    remarks=line_in.remarks.strip() if line_in.remarks else None,
                )
            )

    try:
        db.commit()
        db.refresh(db_receipt)
        return db_receipt
    except Exception:
        db.rollback()
        raise


def delete_receipt(db: Session, receipt_id: int) -> Optional[Receipt]:
    db_receipt = get_receipt_by_id(db, receipt_id)
    if not db_receipt:
        return None

    if db_receipt.status == TransactionStatus.POSTED:
        raise ValueError("Cannot delete a posted Receipt document.")

    db_receipt.is_active = False
    for line in db_receipt.lines:
        line.is_active = False

    try:
        db.commit()
        return db_receipt
    except Exception:
        db.rollback()
        raise
