from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Date, DateTime, Numeric, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import DestinationType, TransactionStatus

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear
    from app.models.indent import Indent
    from app.models.office import Office
    from app.models.section import Section
    from app.models.user import User
    from app.models.item import Item
    from app.models.unit import Unit
    from app.models.asset import Asset
    from app.models.outward_pass import OutwardPass


class Issue(BaseModel):
    __tablename__ = "issues"

    issue_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    issue_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    financial_year_id: Mapped[int] = mapped_column(
        ForeignKey("financial_years.id"),
        nullable=False,
        index=True,
    )

    indent_id: Mapped[int] = mapped_column(
        ForeignKey("indents.id"),
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

    destination_type: Mapped[DestinationType] = mapped_column(
        SqlEnum(DestinationType),
        nullable=False,
        default=DestinationType.INTERNAL,
    )

    status: Mapped[TransactionStatus] = mapped_column(
        SqlEnum(TransactionStatus),
        nullable=False,
        default=TransactionStatus.DRAFT,
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
    indent: Mapped["Indent"] = relationship("Indent")
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

    lines: Mapped[list["IssueLine"]] = relationship(
        "IssueLine",
        back_populates="issue",
        cascade="all, delete-orphan",
    )

    outward_pass: Mapped[Optional["OutwardPass"]] = relationship(
        "OutwardPass",
        back_populates="issue",
        uselist=False,
        cascade="all, delete-orphan",
    )


class IssueLine(BaseModel):
    __tablename__ = "issue_lines"

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
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

    issue: Mapped["Issue"] = relationship("Issue", back_populates="lines")
    item: Mapped["Item"] = relationship("Item")
    unit: Mapped[Optional["Unit"]] = relationship("Unit")

    assets: Mapped[list["IssueLineAsset"]] = relationship(
        "IssueLineAsset",
        back_populates="issue_line",
        cascade="all, delete-orphan",
    )


class IssueLineAsset(BaseModel):
    __tablename__ = "issue_line_assets"

    issue_line_id: Mapped[int] = mapped_column(
        ForeignKey("issue_lines.id"),
        nullable=False,
        index=True,
    )

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    issue_line: Mapped["IssueLine"] = relationship("IssueLine", back_populates="assets")
    asset: Mapped["Asset"] = relationship("Asset")
