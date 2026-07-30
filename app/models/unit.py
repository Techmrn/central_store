from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.item import Item

class Unit(BaseModel):
    __tablename__ = "units"

    name: Mapped[str] = mapped_column(
    String(100),
    unique=True,
    nullable=False,
    index=True, )

    symbol: Mapped[str] = mapped_column(
    String(20),
    unique=True,
    nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    items: Mapped[list["Item"]] = relationship(
    "Item",
    back_populates="unit",
    )