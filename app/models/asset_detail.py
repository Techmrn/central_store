from datetime import date
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.asset import Asset


class AssetDetail(BaseModel):
    __tablename__ = "asset_details"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    make: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    purchase_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    purchase_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    purchase_value: Mapped[Optional[float]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    warranty_expiry_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
    )

    technical_specifications: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="asset_detail",
    )
