from sqlalchemy import String, Date, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime, date

from app.models.base import BaseModel


class FinancialYear(BaseModel):
    __tablename__ = "financial_years"


    year_name: Mapped[str] = mapped_column(
        String(9),
        unique=True,
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    end_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_closed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )