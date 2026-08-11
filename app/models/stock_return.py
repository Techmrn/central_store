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
    from app.models.issue import Issue
    from app.models.item import Item
    from app.models.unit import Unit
    from app.models.asset import Asset


class StockReturn(BaseModel):
    __tablename__ = "stock_returns"

    return_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    return_date: Mapped[date] = mapped_column(
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

    reference_issue_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("issues.id"),
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
    office: Mapped["Office"] = relationship("Office")
    section: Mapped[Optional["Section"]] = relationship("Section")
    reference_issue: Mapped[Optional["Issue"]] = relationship("Issue")

    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    posted_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[posted_by_id],
    )

    lines: Mapped[list["StockReturnLine"]] = relationship(
        "StockReturnLine",
        back_populates="stock_return",
        cascade="all, delete-orphan",
    )


class StockReturnLine(BaseModel):
    __tablename__ = "stock_return_lines"

    return_id: Mapped[int] = mapped_column(
        ForeignKey("stock_returns.id"),
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

    stock_return: Mapped["StockReturn"] = relationship("StockReturn", back_populates="lines")
    item: Mapped["Item"] = relationship("Item")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")

    assets: Mapped[list["StockReturnLineAsset"]] = relationship(
        "StockReturnLineAsset",
        back_populates="return_line",
        cascade="all, delete-orphan",
    )


class StockReturnLineAsset(BaseModel):
    __tablename__ = "stock_return_line_assets"

    return_line_id: Mapped[int] = mapped_column(
        ForeignKey("stock_return_lines.id"),
        nullable=False,
        index=True,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    return_line: Mapped["StockReturnLine"] = relationship("StockReturnLine", back_populates="assets")
    asset: Mapped["Asset"] = relationship("Asset")
