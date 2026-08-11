from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, DateTime, Numeric, Enum as SqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import UnserviceableStatus

if TYPE_CHECKING:
    from app.models.financial_year import FinancialYear
    from app.models.item import Item
    from app.models.office import Office
    from app.models.section import Section
    from app.models.user import User


class UnserviceableMaterial(BaseModel):
    __tablename__ = "unserviceable_materials"

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

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[UnserviceableStatus] = mapped_column(
        SqlEnum(UnserviceableStatus),
        nullable=False,
        default=UnserviceableStatus.UNSERVICEABLE,
        index=True,
    )

    date_reported: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    reference_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    reported_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    financial_year: Mapped["FinancialYear"] = relationship("FinancialYear")
    item: Mapped["Item"] = relationship("Item")
    office: Mapped["Office"] = relationship("Office")
    section: Mapped[Optional["Section"]] = relationship("Section")
    reported_by: Mapped[Optional["User"]] = relationship("User")
