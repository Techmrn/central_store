from sqlalchemy import String, Integer, ForeignKey
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

    specification: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    remarks: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    category = relationship("Category")
    unit = relationship("Unit")