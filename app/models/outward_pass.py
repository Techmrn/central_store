from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.issue import Issue
    from app.models.user import User


class OutwardPass(BaseModel):
    __tablename__ = "outward_passes"

    pass_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    pass_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    issue_id: Mapped[int] = mapped_column(
        ForeignKey("issues.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    recipient_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    destination: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    vehicle_no: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    created_by_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )

    issue: Mapped["Issue"] = relationship("Issue", back_populates="outward_pass")
    created_by: Mapped[Optional["User"]] = relationship("User")
