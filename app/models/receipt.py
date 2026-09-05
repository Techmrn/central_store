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


class Receipt(BaseModel):
    __tablename__ = "receipts"

    receipt_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    receipt_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    financial_year_id: Mapped[int] = mapped_column(
        ForeignKey("financial_years.id"),
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

    supplier_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    reference_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
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
    office: Mapped["Office"] = relationship("Office")
    section: Mapped[Optional["Section"]] = relationship("Section")

    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    posted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[posted_by_id],
    )

    lines: Mapped[list["ReceiptLine"]] = relationship(
        "ReceiptLine",
        back_populates="receipt",
        cascade="all, delete-orphan",
    )


class ReceiptLine(BaseModel):
    __tablename__ = "receipt_lines"

    receipt_id: Mapped[int] = mapped_column(
        ForeignKey("receipts.id"),
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

    unit_price: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="lines")
    item: Mapped["Item"] = relationship("Item")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")

    asset_entries: Mapped[list["ReceiptLineAsset"]] = relationship(
        "ReceiptLineAsset",
        back_populates="receipt_line",
        cascade="all, delete-orphan",
    )


class ReceiptLineAsset(BaseModel):
    """Draft receipt-time details for one physical Asset to be created on posting."""

    __tablename__ = "receipt_line_assets"

    receipt_line_id: Mapped[int] = mapped_column(
        ForeignKey("receipt_lines.id"),
        nullable=False,
        index=True,
    )

    asset_no: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serial_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    make: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_value: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    warranty_expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    technical_specifications: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    receipt_line: Mapped["ReceiptLine"] = relationship(
        "ReceiptLine",
        back_populates="asset_entries",
    )
