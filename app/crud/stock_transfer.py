from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.office import Office
from app.models.section import Section
from app.models.stock_transfer import StockTransfer, StockTransferLine, StockTransferLineAsset
from app.schemas.stock_transfer import StockTransferCreate, StockTransferUpdate
from app.services.document_number_service import generate_document_number


def create_transfer(
    db: Session,
    transfer_in: StockTransferCreate,
    user_id: Optional[int] = None,
) -> StockTransfer:
    from_office = db.query(Office).filter(Office.id == transfer_in.from_office_id, Office.is_active == True).first()
    to_office = db.query(Office).filter(Office.id == transfer_in.to_office_id, Office.is_active == True).first()

    if not from_office or not to_office:
        raise ValueError("Source or destination office not found.")

    if transfer_in.from_office_id == transfer_in.to_office_id and transfer_in.from_section_id == transfer_in.to_section_id:
        raise ValueError("Source and destination locations cannot be identical.")

    if transfer_in.transfer_no:
        clean_no = transfer_in.transfer_no.strip()
        existing = db.query(StockTransfer).filter(func.lower(StockTransfer.transfer_no) == clean_no.lower()).first()
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
    return db.query(StockTransfer).filter(StockTransfer.id == transfer_id, StockTransfer.is_active == True).first()


def get_all_transfers(
    db: Session,
    search: str = "",
    transfer_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    from_office_id: Optional[int] = None,
    to_office_id: Optional[int] = None,
    status: Optional[TransactionStatus] = None,
    page: int = 1,
):
    query = (
        db.query(StockTransfer)
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

    if transfer_in.remarks is not None:
        db_transfer.remarks = transfer_in.remarks.strip() if transfer_in.remarks else None

    if transfer_in.lines is not None:
        db_transfer.lines.clear()
        for line_in in transfer_in.lines:
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
