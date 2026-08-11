from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import MovementType, TransactionSource

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear
    from app.models.item import Item
    from app.models.office import Office
    from app.models.section import Section


class StockMovement(BaseModel):
    __tablename__ = "stock_movements"

    financial_year_id: Mapped[int] = mapped_column(
        ForeignKey("financial_years.id"),
        nullable=False,
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )

    office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    movement_type: Mapped[MovementType] = mapped_column(
        SqlEnum(MovementType),
        nullable=False,
        index=True,
    )

    transaction_source: Mapped[TransactionSource] = mapped_column(
        SqlEnum(TransactionSource),
        nullable=False,
        default=TransactionSource.OPERATIONAL,
        index=True,
    )

    quantity_in: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0.0,
    )

    quantity_out: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0.0,
    )

    movement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    reference_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reference_id: Mapped[int] = mapped_column(
        nullable=False,
        index=True,
    )

    reference_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    financial_year: Mapped["FinancialYear"] = relationship("FinancialYear")
    item: Mapped["Item"] = relationship("Item")
    office: Mapped["Office"] = relationship("Office")
    section: Mapped[Optional["Section"]] = relationship("Section")
