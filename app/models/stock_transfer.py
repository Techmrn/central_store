from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Date, DateTime, Numeric, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import TransactionStatus

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear
    from app.models.office import Office
    from app.models.section import Section
    from app.models.user import User
    from app.models.item import Item
    from app.models.unit import Unit
    from app.models.asset import Asset


class StockTransfer(BaseModel):
    __tablename__ = "stock_transfers"

    transfer_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    transfer_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    financial_year_id: Mapped[int] = mapped_column(
        ForeignKey("financial_years.id"),
        nullable=False,
        index=True,
    )

    from_office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
        index=True,
    )

    from_section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    to_office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
        index=True,
    )

    to_section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    status: Mapped[TransactionStatus] = mapped_column(
        SqlEnum(TransactionStatus),
        nullable=False,
        default=TransactionStatus.DRAFT,
        index=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    posted_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    financial_year: Mapped["FinancialYear"] = relationship("FinancialYear")
    from_office: Mapped["Office"] = relationship("Office", foreign_keys=[from_office_id])
    from_section: Mapped[Optional["Section"]] = relationship("Section", foreign_keys=[from_section_id])
    to_office: Mapped["Office"] = relationship("Office", foreign_keys=[to_office_id])
    to_section: Mapped[Optional["Section"]] = relationship("Section", foreign_keys=[to_section_id])

    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    posted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[posted_by_id],
    )

    lines: Mapped[list["StockTransferLine"]] = relationship(
        "StockTransferLine",
        back_populates="transfer",
        cascade="all, delete-orphan",
    )


class StockTransferLine(BaseModel):
    __tablename__ = "stock_transfer_lines"

    transfer_id: Mapped[int] = mapped_column(
        ForeignKey("stock_transfers.id"),
        nullable=False,
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )

    unit_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("units.id"),
        nullable=True,
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    transfer: Mapped["StockTransfer"] = relationship("StockTransfer", back_populates="lines")
    item: Mapped["Item"] = relationship("Item")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")

    assets: Mapped[list["StockTransferLineAsset"]] = relationship(
        "StockTransferLineAsset",
        back_populates="transfer_line",
        cascade="all, delete-orphan",
    )


class StockTransferLineAsset(BaseModel):
    __tablename__ = "stock_transfer_line_assets"

    transfer_line_id: Mapped[int] = mapped_column(
        ForeignKey("stock_transfer_lines.id"),
        nullable=False,
        index=True,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    transfer_line: Mapped["StockTransferLine"] = relationship("StockTransferLine", back_populates="assets")
    asset: Mapped["Asset"] = relationship("Asset")
