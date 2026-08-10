from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Section(BaseModel):
    __tablename__ = "sections"

    office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    remarks: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    office: Mapped["Office"] = relationship(
        back_populates="sections",
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
    )

    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        back_populates="section",
    )

