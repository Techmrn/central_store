from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OpeningStockBase(BaseModel):
    financial_year_id: int
    office_id: int
    item_id: int
    quantity: Decimal
    unit_rate: Decimal
    remarks: Optional[str] = None


class OpeningStockCreate(OpeningStockBase):
    pass


class OpeningStockUpdate(BaseModel):
    financial_year_id: Optional[int] = None
    office_id: Optional[int] = None
    item_id: Optional[int] = None
    quantity: Optional[Decimal] = None
    unit_rate: Optional[Decimal] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None


class OpeningStockRead(OpeningStockBase):
    id: int
    total_value: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)