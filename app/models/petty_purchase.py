from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import TransactionStatus

if TYPE_CHECKING:
    from app.models.indent import Indent
    from app.models.indent_line import IndentLine
    from app.models.item import Item
    from app.models.user import User


class PettyPurchase(BaseModel):
    """A local purchase made specifically to fulfil an Indent line.

    Petty purchases are not Central Store stock movements.  They are kept as
    an auditable purchase record and are consumed by the linked Issue.
    One active petty purchase record is allowed per IndentLine.
    """

    __tablename__ = "petty_purchases"

    petty_purchase_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    indent_id: Mapped[int] = mapped_column(
        ForeignKey("indents.id"),
        nullable=False,
        index=True,
    )

    indent_line_id: Mapped[int] = mapped_column(
        ForeignKey("indent_lines.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    purchase_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    supplier_name: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )

    reference_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    unit_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    total_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
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

    posted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    indent: Mapped["Indent"] = relationship("Indent")
    indent_line: Mapped["IndentLine"] = relationship(
        "IndentLine",
        back_populates="petty_purchase",
    )
    item: Mapped["Item"] = relationship("Item")
    created_by: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by_id],
    )
