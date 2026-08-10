from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.indent import Indent
    from app.models.item import Item


class IndentLine(BaseModel):
    __tablename__ = "indent_lines"
    __table_args__ = (
        UniqueConstraint(
            "indent_id",
            "item_id",
            name="uq_indent_line_item",
        ),
    )

    indent_id: Mapped[int] = mapped_column(
        ForeignKey("indents.id"),
        nullable=False,
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )

    requested_quantity: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    issued_quantity: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0.0,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    indent: Mapped["Indent"] = relationship(
        "Indent",
        back_populates="lines",
    )

    item: Mapped["Item"] = relationship(
        "Item",
    )
