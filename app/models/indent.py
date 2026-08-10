from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Date, DateTime, Enum as SqlEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import IndentStatus, RequestSource

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear
    from app.models.office import Office
    from app.models.section import Section
    from app.models.indent_line import IndentLine
    from app.models.user import User


class Indent(BaseModel):
    __tablename__ = "indents"
    __table_args__ = (
        UniqueConstraint(
            "financial_year_id",
            "office_id",
            "indent_no",
            name="uq_indent_fy_office_no",
        ),
    )

    indent_no: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    indent_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    received_date: Mapped[date] = mapped_column(
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

    request_source: Mapped[RequestSource] = mapped_column(
        SqlEnum(RequestSource),
        nullable=False,
        default=RequestSource.PHYSICAL,
    )

    reference_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    status: Mapped[IndentStatus] = mapped_column(
        SqlEnum(IndentStatus),
        nullable=False,
        default=IndentStatus.DRAFT,
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

    processed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    closed_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    financial_year: Mapped["FinancialYear"] = relationship("FinancialYear")
    office: Mapped["Office"] = relationship("Office")
    section: Mapped[Optional["Section"]] = relationship("Section")

    lines: Mapped[list["IndentLine"]] = relationship(
        "IndentLine",
        back_populates="indent",
        cascade="all, delete-orphan",
    )

    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
    processed_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[processed_by_id],
    )
    closed_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[closed_by_id],
    )
