from sqlalchemy import Column, Integer, Numeric, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class OpeningStock(BaseModel):
    __tablename__ = "opening_stocks"

    financial_year_id = Column(
        Integer,
        ForeignKey("financial_years.id"),
        nullable=False,
    )

    office_id = Column(
        Integer,
        ForeignKey("offices.id"),
        nullable=False,
    )

    item_id = Column(
        Integer,
        ForeignKey("items.id"),
        nullable=False,
    )

    quantity = Column(
        Numeric(15, 3),
        nullable=False,
    )

    unit_rate = Column(
        Numeric(15, 2),
        nullable=False,
    )

    total_value = Column(
        Numeric(18, 2),
        nullable=False,
    )

    remarks = Column(
        Text,
        nullable=True,
    )

    financial_year = relationship("FinancialYear")
    office = relationship("Office")
    item = relationship("Item")