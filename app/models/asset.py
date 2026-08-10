from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import AssetStatus

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.office import Office
    from app.models.section import Section
    from app.models.asset_detail import AssetDetail
    from app.models.asset_movement import AssetMovement


class Asset(BaseModel):
    __tablename__ = "assets"

    # id, created_at, updated_at, is_active inherited from BaseModel

    asset_no: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"),
        nullable=False,
        index=True,
    )

    serial_no: Mapped[Optional[str]] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
    )

    office_id: Mapped[int] = mapped_column(
        ForeignKey("offices.id"),
        nullable=False,
        index=True,
    )

    section_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sections.id"),
        nullable=True,
        index=True,
    )

    status: Mapped[AssetStatus] = mapped_column(
        SqlEnum(AssetStatus),
        nullable=False,
        default=AssetStatus.IN_STORE,
        index=True,
    )

    remarks: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    item: Mapped["Item"] = relationship(
        "Item",
        back_populates="assets",
    )

    office: Mapped["Office"] = relationship(
        "Office",
        back_populates="assets",
    )

    section: Mapped[Optional["Section"]] = relationship(
        "Section",
        back_populates="assets",
    )

    asset_detail: Mapped[Optional["AssetDetail"]] = relationship(
        "AssetDetail",
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan",
    )

    movements: Mapped[list["AssetMovement"]] = relationship(
        "AssetMovement",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
