from enum import Enum

from sqlalchemy import Enum as SqlEnum, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel



class OfficeType(str, Enum):
    DIRECTORATE = "Directorate"
    GCP = "Government Central Press"
    BRANCH = "Branch"
    DISTRICT_FORM_STORE = "District Form Store"



class Office(BaseModel):
    __tablename__ = "offices"

    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    office_type:  Mapped[OfficeType] = mapped_column(
        SqlEnum(OfficeType),
        nullable=False,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    remarks: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    sections: Mapped[list["Section"]] = relationship(
    back_populates="office"
)