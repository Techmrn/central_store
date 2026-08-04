from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Permission(BaseModel):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    module: Mapped[str] = mapped_column(
        String(50),
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )