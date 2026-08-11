from typing import Type
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.financial_year import FinancialYear


def generate_document_number(
    db: Session,
    model_class: Type,
    number_field_name: str,
    prefix: str,
    financial_year_id: int,
) -> str:
    """
    Generate a sequential document number per financial year.
    Format: PREFIX-YYYY-XXXX (e.g. ISS-2026-0001)
    """
    fy = db.query(FinancialYear).filter(FinancialYear.id == financial_year_id).first()
    year_str = "2026"
    if fy and fy.year_name:
        year_str = fy.year_name.split("-")[0].strip()

    pattern = f"{prefix}-{year_str}-%"

    field_attr = getattr(model_class, number_field_name)

    latest_doc = (
        db.query(field_attr)
        .filter(field_attr.like(pattern))
        .order_by(field_attr.desc())
        .first()
    )

    if latest_doc and latest_doc[0]:
        last_number_str = latest_doc[0]
        try:
            seq = int(last_number_str.split("-")[-1]) + 1
        except ValueError:
            seq = 1
    else:
        seq = 1

    return f"{prefix}-{year_str}-{seq:04d}"
