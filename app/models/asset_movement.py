from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, DateTime, Enum as SqlEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AssetMovementType

if TYPE_CHECKING:
    from app.models.asset import Asset
    from app.models.office import Office
    from app.models.section import Section


class AssetMovement(BaseModel):
    __tablename__ = "asset_movements"

    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    movement_type: Mapped[AssetMovementType] = mapped_column(
        SqlEnum(AssetMovementType),
        nullable=False,
    )

    from_office_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("offices.id"),
        nullable=True,
        index=True,
    )

    from_section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    to_office_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("offices.id"),
        nullable=True,
        index=True,
    )

    to_section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    reference_document: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )

    movement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="movements",
    )

    from_office: Mapped[Optional["Office"]] = relationship(
        "Office",
        foreign_keys=[from_office_id],
    )

    from_section: Mapped[Optional["Section"]] = relationship(
        "Section",
        foreign_keys=[from_section_id],
    )

    to_office: Mapped[Optional["Office"]] = relationship(
        "Office",
        foreign_keys=[to_office_id],
    )

    to_section: Mapped[Optional["Section"]] = relationship(
        "Section",
        foreign_keys=[to_section_id],
    )
