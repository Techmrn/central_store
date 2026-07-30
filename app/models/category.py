from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import Category_Type

class Category(BaseModel):
    __tablename__ = "categories"

    #id,created_at,updated_at,is_active: will come from BaseModel

    code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
   
    type: Mapped[Category_Type] = mapped_column(
        Enum(Category_Type), # from app/models/enums.py
        nullable=False
    )

    items: Mapped[list["Item"]] = relationship(
        "Item",
        back_populates="category"
    )