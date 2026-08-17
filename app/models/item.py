from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel



class Item(BaseModel):
    __tablename__ = "items"

    # id, created_at, updated_at, is_active
    # are inherited from BaseModel

    code: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"),
        nullable=False,
    )

    unit_id: Mapped[int] = mapped_column(
        ForeignKey("units.id"),
        nullable=False,
    )

    is_temporary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    specification: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="items",
    )

    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="items",
    )

    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="item",
    )