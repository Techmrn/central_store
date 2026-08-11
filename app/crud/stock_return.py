from datetime import date
from typing import Optional
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.pagination import get_pagination_result
from app.models.enums import TransactionStatus
from app.models.financial_year import FinancialYear
from app.models.office import Office
from app.models.stock_return import StockReturn, StockReturnLine, StockReturnLineAsset
from app.schemas.stock_return import StockReturnCreate, StockReturnUpdate
from app.services.document_number_service import generate_document_number


def create_return(
    db: Session,
    return_in: StockReturnCreate,
    user_id: Optional[int] = None,
) -> StockReturn:
    office = db.query(Office).filter(Office.id == return_in.office_id, Office.is_active == True).first()
    if not office:
        raise ValueError("Office not found.")

    if return_in.return_no:
        clean_no = return_in.return_no.strip()
        existing = db.query(StockReturn).filter(func.lower(StockReturn.return_no) == clean_no.lower()).first()
        if existing:
            raise ValueError(f"Return number '{clean_no}' already exists.")
        return_no = clean_no
    else:
        return_no = generate_document_number(
            db=db,
            model_class=StockReturn,
            number_field_name="return_no",
            prefix="RET",
            financial_year_id=return_in.financial_year_id,
        )

    return_date = return_in.return_date or date.today()

    db_return = StockReturn(
        return_no=return_no,
        return_date=return_date,
        financial_year_id=return_in.financial_year_id,
        office_id=return_in.office_id,
        section_id=return_in.section_id,
        reference_issue_id=return_in.reference_issue_id,
        status=TransactionStatus.DRAFT,
        remarks=return_in.remarks.strip() if return_in.remarks else None,
        created_by_id=user_id,
    )

    for line_in in return_in.lines:
        db_line = StockReturnLine(
            item_id=line_in.item_id,
            unit_id=line_in.unit_id,
            quantity=line_in.quantity,
            remarks=line_in.remarks.strip() if line_in.remarks else None,
        )

        if line_in.asset_ids:
            for aid in line_in.asset_ids:
                db_line.assets.append(StockReturnLineAsset(asset_id=aid))

        db_return.lines.append(db_line)

    db.add(db_return)
    try:
        db.commit()
        db.refresh(db_return)
        return db_return
    except Exception:
        db.rollback()
        raise


def get_return_by_id(db: Session, return_id: int) -> Optional[StockReturn]:
    return db.query(StockReturn).filter(StockReturn.id == return_id, StockReturn.is_active == True).first()


def get_all_returns(
    db: Session,
    search: str = "",
    return_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    status: Optional[TransactionStatus] = None,
    page: int = 1,
):
    query = (
        db.query(StockReturn)
        .join(Office, StockReturn.office_id == Office.id)
        .join(FinancialYear, StockReturn.financial_year_id == FinancialYear.id)
        .filter(
            StockReturn.is_active == True,
            Office.is_active == True,
            FinancialYear.is_active == True,
        )
    )

    if return_no:
        query = query.filter(func.lower(StockReturn.return_no) == return_no.strip().lower())

    if financial_year_id is not None:
        query = query.filter(StockReturn.financial_year_id == financial_year_id)

    if office_id is not None:
        query = query.filter(StockReturn.office_id == office_id)

    if status is not None:
        query = query.filter(StockReturn.status == status)

    if search:
        clean = search.strip()
        query = query.filter(
            or_(
                StockReturn.return_no.ilike(f"%{clean}%"),
                Office.name.ilike(f"%{clean}%"),
            )
        )

    query = query.order_by(StockReturn.id.desc())
    return get_pagination_result(query, page)


def update_return(
    db: Session,
    return_id: int,
    return_in: StockReturnUpdate,
) -> StockReturn:
    db_return = get_return_by_id(db, return_id)
    if not db_return:
        raise ValueError("Return document not found.")

    if db_return.status == TransactionStatus.POSTED:
        raise ValueError("Cannot update a posted Return document.")

    if return_in.reference_issue_id is not None:
        db_return.reference_issue_id = return_in.reference_issue_id

    if return_in.remarks is not None:
        db_return.remarks = return_in.remarks.strip() if return_in.remarks else None

    if return_in.lines is not None:
        db_return.lines.clear()
        for line_in in return_in.lines:
            db_line = StockReturnLine(
                item_id=line_in.item_id,
                unit_id=line_in.unit_id,
                quantity=line_in.quantity,
                remarks=line_in.remarks.strip() if line_in.remarks else None,
            )
            if line_in.asset_ids:
                for aid in line_in.asset_ids:
                    db_line.assets.append(StockReturnLineAsset(asset_id=aid))
            db_return.lines.append(db_line)

    try:
        db.commit()
        db.refresh(db_return)
        return db_return
    except Exception:
        db.rollback()
        raise
