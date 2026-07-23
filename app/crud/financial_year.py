from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.financial_year import FinancialYear
from app.schemas.financial_year import (
    FinancialYearCreate,
    FinancialYearUpdate,
)


def generate_year_name(start_date, end_date):
    """
    Generates year name in the format:
    2026-27
    """
    return f"{start_date.year}-{str(end_date.year)[-2:]}"


def get_all_financial_years(db: Session):
    return (
        db.query(FinancialYear)
        .order_by(FinancialYear.start_date.desc())
        .all()
    )


def get_financial_year_by_id(db: Session, financial_year_id: int):
    return (
        db.query(FinancialYear)
        .filter(FinancialYear.id == financial_year_id)
        .first()
    )


def create_financial_year(
    db: Session,
    financial_year: FinancialYearCreate,
):
    # Validate dates
    if financial_year.start_date >= financial_year.end_date:
        raise ValueError("Start date must be earlier than end date.")

    year_name = generate_year_name(
        financial_year.start_date,
        financial_year.end_date,
    )

    # Duplicate check
    duplicate = (
        db.query(FinancialYear)
        .filter(
            func.lower(FinancialYear.year_name)
            == year_name.lower()
        )
        .first()
    )

    if duplicate:
        return None

    # Only one current financial year
    db.query(FinancialYear).update(
        {"is_current": False}
    )

    db_financial_year = FinancialYear(
        year_name=year_name,
        start_date=financial_year.start_date,
        end_date=financial_year.end_date,
        is_current=True,
    )

    db.add(db_financial_year)
    db.commit()
    db.refresh(db_financial_year)

    return db_financial_year


def update_financial_year(
    db: Session,
    financial_year_id: int,
    financial_year: FinancialYearUpdate,
):
    db_financial_year = get_financial_year_by_id(
        db,
        financial_year_id,
    )

    if not db_financial_year:
        return None

    if financial_year.start_date >= financial_year.end_date:
        raise ValueError("Start date must be earlier than end date.")

    year_name = generate_year_name(
        financial_year.start_date,
        financial_year.end_date,
    )

    duplicate = (
        db.query(FinancialYear)
        .filter(
            func.lower(FinancialYear.year_name)
            == year_name.lower(),
            FinancialYear.id != financial_year_id,
        )
        .first()
    )

    if duplicate:
        return False

    # Ensure only one current year
    if financial_year.is_current:
        db.query(FinancialYear).update(
            {"is_current": False}
        )

    db_financial_year.year_name = year_name
    db_financial_year.start_date = financial_year.start_date
    db_financial_year.end_date = financial_year.end_date
    db_financial_year.is_current = financial_year.is_current
    db_financial_year.is_closed = financial_year.is_closed
    db_financial_year.is_active = financial_year.is_active

    db.commit()
    db.refresh(db_financial_year)

    return db_financial_year


def delete_financial_year(
    db: Session,
    financial_year_id: int,
):
    db_financial_year = get_financial_year_by_id(
        db,
        financial_year_id,
    )

    if not db_financial_year:
        return None

    db_financial_year.is_active = False

    db.commit()
    db.refresh(db_financial_year)

    return db_financial_year