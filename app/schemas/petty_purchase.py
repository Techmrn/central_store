from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import TransactionStatus


class PettyPurchaseCreate(BaseModel):
    purchase_date: Optional[date] = None
    supplier_name: Optional[str] = None
    reference_no: Optional[str] = None
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    remarks: Optional[str] = None


class PettyPurchaseUpdate(PettyPurchaseCreate):
    quantity: Optional[float] = Field(default=None, gt=0)


class PettyPurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    petty_purchase_no: str
    indent_id: int
    indent_line_id: int
    item_id: int
    quantity: float
    purchase_date: date
    supplier_name: Optional[str] = None
    reference_no: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    status: TransactionStatus
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
