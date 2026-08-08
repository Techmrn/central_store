from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    code: Mapped[str] = mapped_column(
        String(7),
        unique=True,
        nullable=False,
        index=True,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    designation: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
    )

    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
    )

    email: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    mobile: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    last_login: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    office: Mapped["Office"] = relationship(
        back_populates="users",
    )

    section: Mapped[Optional["Section"]] = relationship(
        back_populates="users",
    )

    user_roles: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
    )

    login_history: Mapped[list["LoginHistory"]] = relationship(
        back_populates="user",
    )