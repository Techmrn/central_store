from datetime import datetime
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.enums import IndentStatus, RequestSource, FulfillmentType, Category_Type, TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.indent import Indent
from app.models.indent_line import IndentLine
from app.models.item import Item
from app.models.category import Category
from app.models.petty_purchase import PettyPurchase
from app.models.office import Office
from app.models.section import Section
from app.schemas.indent import (
    IndentCreate,
    IndentLineCreate,
    IndentUpdate,
)


def _validate_office_and_section(
    db: Session,
    office_id: int,
    section_id: Optional[int] = None,
):
    office = (
        db.query(Office)
        .filter(
            Office.id == office_id,
            Office.is_active == True,
        )
        .first()
    )
    if not office:
        raise ValueError("Office not found.")

    if section_id is not None:
        section = (
            db.query(Section)
            .filter(
                Section.id == section_id,
                Section.is_active == True,
            )
            .first()
        )
        if not section:
            raise ValueError("Section not found.")
        if section.office_id != office_id:
            raise ValueError("The selected section does not belong to the specified office.")


def _validate_financial_year(db: Session, financial_year_id: int):
    fy = (
        db.query(FinancialYear)
        .filter(
            FinancialYear.id == financial_year_id,
            FinancialYear.is_active == True,
        )
        .first()
    )
    if not fy:
        raise ValueError("Financial year not found.")


def _validate_items_and_quantities(db: Session, lines: list[IndentLineCreate]):
    if not lines:
        raise ValueError("Indent must contain at least one line item.")

    item_ids = [l.item_id for l in lines]
    if len(item_ids) != len(set(item_ids)):
        raise ValueError("Duplicate items in the same indent are not allowed.")

    for l in lines:
        if l.requested_quantity <= 0:
            raise ValueError(f"Requested quantity must be greater than 0 for item ID {l.item_id}.")
        
        issued = l.issued_quantity if l.issued_quantity is not None else 0.0
        if issued < 0:
            raise ValueError(f"Issued quantity cannot be negative for item ID {l.item_id}.")
        if issued > l.requested_quantity:
            raise ValueError(
                f"Issued quantity ({issued}) cannot exceed requested quantity ({l.requested_quantity}) for item ID {l.item_id}."
            )

        item = (
            db.query(Item)
            .join(Category, Item.category_id == Category.id)
            .filter(
                Item.id == l.item_id,
                Item.is_active == True,
                Category.is_active == True,
            )
            .first()
        )
        if not item:
            raise ValueError(f"Item ID {l.item_id} not found.")

        if l.fulfillment_type == FulfillmentType.PETTY_PURCHASE and item.category.type != Category_Type.MATERIAL:
            raise ValueError(
                f"Asset item '{item.name}' cannot be fulfilled through Petty Purchase."
            )


def create_indent(
    db: Session,
    indent_in: IndentCreate,
    user_id: Optional[int] = None,
) -> Indent:
    clean_indent_no = indent_in.indent_no.strip()

    # Check unique constraint: (financial_year_id, office_id, indent_no)
    existing = (
        db.query(Indent)
        .filter(
            Indent.financial_year_id == indent_in.financial_year_id,
            Indent.office_id == indent_in.office_id,
            func.lower(Indent.indent_no) == clean_indent_no.lower(),
        )
        .first()
    )

    if existing:
        raise ValueError(
            f"Indent number '{clean_indent_no}' already exists for this office and financial year."
        )

    # Validations
    _validate_financial_year(db, indent_in.financial_year_id)
    _validate_office_and_section(db, indent_in.office_id, indent_in.section_id)
    _validate_items_and_quantities(db, indent_in.lines)

    db_indent = Indent(
        indent_no=clean_indent_no,
        indent_date=indent_in.indent_date,
        received_date=indent_in.received_date,
        financial_year_id=indent_in.financial_year_id,
        office_id=indent_in.office_id,
        section_id=indent_in.section_id,
        request_source=indent_in.request_source or RequestSource.PHYSICAL,
        reference_no=indent_in.reference_no.strip() if indent_in.reference_no else None,
        status=IndentStatus.DRAFT,
        remarks=indent_in.remarks.strip() if indent_in.remarks else None,
        created_by_id=user_id,
    )

    for line_in in indent_in.lines:
        issued_qty = line_in.issued_quantity if line_in.issued_quantity is not None else 0.0
        db_indent.lines.append(
            IndentLine(
                item_id=line_in.item_id,
                requested_quantity=line_in.requested_quantity,
                issued_quantity=issued_qty,
                fulfillment_type=line_in.fulfillment_type,
                remarks=line_in.remarks.strip() if line_in.remarks else None,
            )
        )

    db.add(db_indent)

    try:
        db.commit()
        db.refresh(db_indent)
        return db_indent
    except Exception:
        db.rollback()
        raise


def get_indent_by_id(db: Session, indent_id: int) -> Optional[Indent]:
    return (
        db.query(Indent)
        .filter(
            Indent.id == indent_id,
            Indent.is_active == True,
        )
        .first()
    )


def get_all_indents(
    db: Session,
    search: str = "",
    indent_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    status: Optional[IndentStatus] = None,
    request_source: Optional[RequestSource] = None,
    page: int = 1,
):
    query = (
        db.query(Indent)
        .join(Office, Indent.office_id == Office.id)
        .join(FinancialYear, Indent.financial_year_id == FinancialYear.id)
        .filter(
            Indent.is_active == True,
            Office.is_active == True,
            FinancialYear.is_active == True,
        )
    )

    if indent_no:
        clean_no = indent_no.strip()
        query = query.filter(func.lower(Indent.indent_no) == clean_no.lower())

    if financial_year_id is not None:
        query = query.filter(Indent.financial_year_id == financial_year_id)

    if office_id is not None:
        query = query.filter(Indent.office_id == office_id)

    if section_id is not None:
        query = query.filter(Indent.section_id == section_id)

    if status is not None:
        query = query.filter(Indent.status == status)

    if request_source is not None:
        query = query.filter(Indent.request_source == request_source)

    if search:
        clean_search = search.strip()
        query = query.filter(
            or_(
                Indent.indent_no.ilike(f"%{clean_search}%"),
                Indent.reference_no.ilike(f"%{clean_search}%"),
                Office.name.ilike(f"%{clean_search}%"),
            )
        )

    query = query.order_by(Indent.id.desc())

    return get_pagination_result(query, page)


def update_indent(
    db: Session,
    indent_id: int,
    indent_in: IndentUpdate,
    user_id: Optional[int] = None,
) -> Indent:
    db_indent = get_indent_by_id(db, indent_id)

    if not db_indent:
        raise ValueError("Indent not found.")

    if db_indent.status == IndentStatus.CLOSED:
        raise ValueError("Cannot modify a closed indent.")

    target_office_id = (
        indent_in.office_id if indent_in.office_id is not None else db_indent.office_id
    )
    target_section_id = (
        indent_in.section_id if indent_in.section_id is not None else db_indent.section_id
    )
    target_fy_id = (
        indent_in.financial_year_id
        if indent_in.financial_year_id is not None
        else db_indent.financial_year_id
    )
    target_indent_no = (
        indent_in.indent_no.strip() if indent_in.indent_no is not None else db_indent.indent_no
    )

    if indent_in.office_id is not None or indent_in.section_id is not None:
        _validate_office_and_section(db, target_office_id, target_section_id)
        db_indent.office_id = target_office_id
        db_indent.section_id = target_section_id

    if indent_in.financial_year_id is not None:
        _validate_financial_year(db, target_fy_id)
        db_indent.financial_year_id = target_fy_id

    # Check unique constraint if FY, office, or indent_no changed
    if (
        indent_in.indent_no is not None
        or indent_in.office_id is not None
        or indent_in.financial_year_id is not None
    ):
        existing = (
            db.query(Indent)
            .filter(
                Indent.financial_year_id == target_fy_id,
                Indent.office_id == target_office_id,
                func.lower(Indent.indent_no) == target_indent_no.lower(),
                Indent.id != indent_id,
                Indent.is_active == True,
            )
            .first()
        )
        if existing:
            raise ValueError(
                f"Indent number '{target_indent_no}' already exists for this office and financial year."
            )
        db_indent.indent_no = target_indent_no

    if indent_in.indent_date is not None:
        db_indent.indent_date = indent_in.indent_date

    if indent_in.received_date is not None:
        db_indent.received_date = indent_in.received_date

    if indent_in.request_source is not None:
        db_indent.request_source = indent_in.request_source

    if indent_in.reference_no is not None:
        db_indent.reference_no = (
            indent_in.reference_no.strip() if indent_in.reference_no else None
        )

    if indent_in.remarks is not None:
        db_indent.remarks = indent_in.remarks.strip() if indent_in.remarks else None

    if indent_in.status is not None and indent_in.status != IndentStatus.CLOSED:
        db_indent.status = indent_in.status

    # Process line updates (Modifies issued_quantity and remarks ONLY, preserving requested_quantity!)
    if indent_in.lines is not None:
        lines_by_id = {line.id: line for line in db_indent.lines if line.is_active}

        for line_update in indent_in.lines:
            if line_update.id not in lines_by_id:
                raise ValueError(f"Indent line ID {line_update.id} not found in this indent.")

            db_line = lines_by_id[line_update.id]

            if line_update.issued_quantity is not None:
                new_issued = line_update.issued_quantity
                if new_issued < 0:
                    raise ValueError(f"Issued quantity cannot be negative for item ID {db_line.item_id}.")
                if new_issued > db_line.requested_quantity:
                    raise ValueError(
                        f"Issued quantity ({new_issued}) cannot exceed requested quantity ({db_line.requested_quantity}) for item ID {db_line.item_id}."
                    )
                db_line.issued_quantity = new_issued

            if line_update.fulfillment_type is not None:
                new_fulfillment = line_update.fulfillment_type

                # Fulfillment is line-level business behavior. Petty Purchase
                # is supported only for MATERIAL items.
                item = (
                    db.query(Item)
                    .join(Category, Item.category_id == Category.id)
                    .filter(
                        Item.id == db_line.item_id,
                        Item.is_active == True,
                        Category.is_active == True,
                    )
                    .first()
                )
                if not item:
                    raise ValueError(f"Item ID {db_line.item_id} not found.")
                if new_fulfillment == FulfillmentType.PETTY_PURCHASE and item.category.type != Category_Type.MATERIAL:
                    raise ValueError(
                        f"Asset item '{item.name}' cannot be fulfilled through Petty Purchase."
                    )

                # A draft petty purchase belongs one-to-one to the IndentLine.
                # When switching back to STOCK, hide the pending purchase; when
                # switched to PETTY_PURCHASE again, the same record can be reused.
                existing_petty = db.query(PettyPurchase).filter(
                    PettyPurchase.indent_line_id == db_line.id,
                    PettyPurchase.status != TransactionStatus.POSTED,
                ).first()
                if new_fulfillment == FulfillmentType.STOCK and existing_petty:
                    existing_petty.is_active = False
                elif new_fulfillment == FulfillmentType.PETTY_PURCHASE and existing_petty:
                    existing_petty.is_active = True

                db_line.fulfillment_type = new_fulfillment

            if line_update.remarks is not None:
                db_line.remarks = line_update.remarks.strip() if line_update.remarks else None

        # Transition to PROCESSING status if currently DRAFT
        if db_indent.status == IndentStatus.DRAFT:
            db_indent.status = IndentStatus.PROCESSING

        db_indent.processed_by_id = user_id
        db_indent.processed_at = func.now()

    try:
        db.commit()
        db.refresh(db_indent)
        return db_indent
    except Exception:
        db.rollback()
        raise


def delete_indent(db: Session, indent_id: int) -> Optional[Indent]:
    db_indent = get_indent_by_id(db, indent_id)

    if db_indent is None:
        return None

    if db_indent.status == IndentStatus.CLOSED:
        raise ValueError("Cannot delete a closed indent.")

    db_indent.is_active = False
    for line in db_indent.lines:
        line.is_active = False

    try:
        db.commit()
        return db_indent
    except Exception:
        db.rollback()
        raise


def close_indent(
    db: Session,
    indent_id: int,
    user_id: Optional[int] = None,
) -> Indent:
    db_indent = get_indent_by_id(db, indent_id)

    if not db_indent:
        raise ValueError("Indent not found.")

    if db_indent.status == IndentStatus.CLOSED:
        raise ValueError("Indent is already closed.")

    active_lines = [l for l in db_indent.lines if l.is_active]
    if not active_lines:
        raise ValueError("Cannot close an indent with no line items.")

    for line in active_lines:
        if line.issued_quantity < 0:
            raise ValueError(f"Invalid negative issued quantity on line ID {line.id}.")
        if line.issued_quantity > line.requested_quantity:
            raise ValueError(
                f"Issued quantity ({line.issued_quantity}) exceeds requested quantity ({line.requested_quantity}) on line ID {line.id}."
            )

    db_indent.status = IndentStatus.CLOSED
    db_indent.closed_by_id = user_id
    db_indent.closed_at = func.now()

    try:
        db.commit()
        db.refresh(db_indent)
        return db_indent
    except Exception:
        db.rollback()
        raise
