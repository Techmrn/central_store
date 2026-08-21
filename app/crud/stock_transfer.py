from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.pagination import get_pagination_result
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.office import Office
from app.models.section import Section
from app.models.stock_transfer import StockTransfer, StockTransferLine, StockTransferLineAsset
from app.schemas.stock_transfer import StockTransferCreate, StockTransferUpdate
from app.services.document_number_service import generate_document_number
from app.services.scope_service import get_stock_office_id


def create_transfer(
    db: Session,
    transfer_in: StockTransferCreate,
    user_id: Optional[int] = None,
) -> StockTransfer:
    from_office = db.query(Office).filter(Office.id == transfer_in.from_office_id, Office.is_active == True).first()
    to_office = db.query(Office).filter(Office.id == transfer_in.to_office_id, Office.is_active == True).first()

    if not from_office or not to_office:
        raise ValueError("Source or destination office not found.")

    from_stock_office_id = get_stock_office_id(db, transfer_in.from_office_id)
    to_stock_office_id = get_stock_office_id(db, transfer_in.to_office_id)

    if from_stock_office_id == to_stock_office_id and transfer_in.from_section_id == transfer_in.to_section_id:
        raise ValueError("Source and destination locations cannot be identical.")

    if not transfer_in.lines:
        raise ValueError("Transfer document must contain at least one line item.")

    if transfer_in.transfer_no:
        clean_no = transfer_in.transfer_no.strip()
        existing = db.query(StockTransfer).filter(
            func.lower(StockTransfer.transfer_no) == clean_no.lower(),
            StockTransfer.is_active == True,
        ).first()
        if existing:
            raise ValueError(f"Transfer number '{clean_no}' already exists.")
        transfer_no = clean_no
    else:
        transfer_no = generate_document_number(
            db=db,
            model_class=StockTransfer,
            number_field_name="transfer_no",
            prefix="TRN",
            financial_year_id=transfer_in.financial_year_id,
        )

    transfer_date = transfer_in.transfer_date or date.today()

    db_transfer = StockTransfer(
        transfer_no=transfer_no,
        transfer_date=transfer_date,
        financial_year_id=transfer_in.financial_year_id,
        from_office_id=transfer_in.from_office_id,
        from_section_id=transfer_in.from_section_id,
        to_office_id=transfer_in.to_office_id,
        to_section_id=transfer_in.to_section_id,
        status=TransactionStatus.DRAFT,
        remarks=transfer_in.remarks.strip() if transfer_in.remarks else None,
        created_by_id=user_id,
    )

    for line_in in transfer_in.lines:
        if line_in.quantity <= 0:
            raise ValueError("Quantity must be greater than zero for all lines.")

        db_line = StockTransferLine(
            item_id=line_in.item_id,
            unit_id=line_in.unit_id,
            quantity=line_in.quantity,
            remarks=line_in.remarks.strip() if line_in.remarks else None,
        )
        if line_in.asset_ids:
            for aid in line_in.asset_ids:
                db_line.assets.append(StockTransferLineAsset(asset_id=aid))
        db_transfer.lines.append(db_line)

    db.add(db_transfer)
    try:
        db.commit()
        db.refresh(db_transfer)
        return db_transfer
    except Exception:
        db.rollback()
        raise


def get_transfer_by_id(db: Session, transfer_id: int) -> Optional[StockTransfer]:
    return (
        db.query(StockTransfer)
        .options(
            joinedload(StockTransfer.from_office),
            joinedload(StockTransfer.from_section),
            joinedload(StockTransfer.to_office),
            joinedload(StockTransfer.to_section),
            joinedload(StockTransfer.financial_year),
            joinedload(StockTransfer.created_by),
            joinedload(StockTransfer.posted_by),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.item),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.unit),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.assets).joinedload(StockTransferLineAsset.asset),
        )
        .filter(StockTransfer.id == transfer_id, StockTransfer.is_active == True)
        .first()
    )


def get_all_transfers(
    db: Session,
    search: str = "",
    transfer_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    from_office_id: Optional[int] = None,
    to_office_id: Optional[int] = None,
    status: Optional[TransactionStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    page: int = 1,
):
    query = (
        db.query(StockTransfer)
        .options(
            joinedload(StockTransfer.from_office),
            joinedload(StockTransfer.from_section),
            joinedload(StockTransfer.to_office),
            joinedload(StockTransfer.to_section),
            joinedload(StockTransfer.financial_year),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.item),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.unit),
            joinedload(StockTransfer.lines).joinedload(StockTransferLine.assets).joinedload(StockTransferLineAsset.asset),
        )
        .join(FinancialYear, StockTransfer.financial_year_id == FinancialYear.id)
        .filter(
            StockTransfer.is_active == True,
            FinancialYear.is_active == True,
        )
    )

    if transfer_no:
        query = query.filter(func.lower(StockTransfer.transfer_no) == transfer_no.strip().lower())

    if financial_year_id is not None:
        query = query.filter(StockTransfer.financial_year_id == financial_year_id)

    if from_office_id is not None:
        query = query.filter(StockTransfer.from_office_id == from_office_id)

    if to_office_id is not None:
        query = query.filter(StockTransfer.to_office_id == to_office_id)

    if status is not None:
        query = query.filter(StockTransfer.status == status)

    if from_date is not None:
        query = query.filter(StockTransfer.transfer_date >= from_date)

    if to_date is not None:
        query = query.filter(StockTransfer.transfer_date <= to_date)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                StockTransfer.transfer_no.ilike(f"%{clean}%"),
                StockTransfer.remarks.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(StockTransfer.id.desc())
    return get_pagination_result(query, page)


def update_transfer(
    db: Session,
    transfer_id: int,
    transfer_in: StockTransferUpdate,
) -> StockTransfer:
    db_transfer = get_transfer_by_id(db, transfer_id)
    if not db_transfer:
        raise ValueError("Transfer document not found.")

    if db_transfer.status == TransactionStatus.POSTED:
        raise ValueError("Cannot update a posted Transfer document.")

    if transfer_in.transfer_date is not None:
        db_transfer.transfer_date = transfer_in.transfer_date

    if transfer_in.from_office_id is not None:
        f_off = db.query(Office).filter(Office.id == transfer_in.from_office_id, Office.is_active == True).first()
        if not f_off:
            raise ValueError("Source office not found.")
        db_transfer.from_office_id = transfer_in.from_office_id

    if transfer_in.to_office_id is not None:
        t_off = db.query(Office).filter(Office.id == transfer_in.to_office_id, Office.is_active == True).first()
        if not t_off:
            raise ValueError("Destination office not found.")
        db_transfer.to_office_id = transfer_in.to_office_id

    if transfer_in.from_section_id is not None:
        db_transfer.from_section_id = transfer_in.from_section_id

    if transfer_in.to_section_id is not None:
        db_transfer.to_section_id = transfer_in.to_section_id

    if db_transfer.from_office_id == db_transfer.to_office_id and db_transfer.from_section_id == db_transfer.to_section_id:
        raise ValueError("Source and destination locations cannot be identical.")

    if transfer_in.remarks is not None:
        db_transfer.remarks = transfer_in.remarks.strip() if transfer_in.remarks else None

    if transfer_in.lines is not None:
        if not transfer_in.lines:
            raise ValueError("Transfer must contain at least one line item.")

        db_transfer.lines.clear()
        for line_in in transfer_in.lines:
            if line_in.quantity <= 0:
                raise ValueError("Quantity must be greater than zero.")

            db_line = StockTransferLine(
                item_id=line_in.item_id,
                unit_id=line_in.unit_id,
                quantity=line_in.quantity,
                remarks=line_in.remarks.strip() if line_in.remarks else None,
            )
            if line_in.asset_ids:
                for aid in line_in.asset_ids:
                    db_line.assets.append(StockTransferLineAsset(asset_id=aid))
            db_transfer.lines.append(db_line)

    try:
        db.commit()
        db.refresh(db_transfer)
        return db_transfer
    except Exception:
        db.rollback()
        raise


def delete_transfer(
    db: Session,
    transfer_id: int,
) -> Optional[StockTransfer]:
    """
    Soft-delete a Stock Transfer. Only DRAFT transfers can be deleted.
    """
    db_transfer = get_transfer_by_id(db, transfer_id)
    if not db_transfer:
        return None

    if db_transfer.status == TransactionStatus.POSTED:
        raise ValueError("Cannot delete a posted Transfer document.")

    db_transfer.is_active = False
    try:
        db.commit()
        return db_transfer
    except Exception:
        db.rollback()
        raise
