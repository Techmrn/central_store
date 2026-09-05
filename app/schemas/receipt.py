from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionStatus


class ReceiptAssetEntryCreate(BaseModel):
    asset_no: Optional[str] = None
    serial_no: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_reference: Optional[str] = None
    purchase_value: Optional[float] = Field(default=None, ge=0)
    warranty_expiry_date: Optional[date] = None
    technical_specifications: Optional[str] = None
    remarks: Optional[str] = None


class ReceiptLineCreate(BaseModel):
    item_id: int
    unit_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    unit_price: Optional[float] = Field(None, ge=0)
    remarks: Optional[str] = None
    asset_entries: list[ReceiptAssetEntryCreate] = []


class ReceiptLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_id: int
    item_id: int
    unit_id: Optional[int] = None
    quantity: float
    unit_price: Optional[float] = None
    remarks: Optional[str] = None
    asset_entries: list[ReceiptAssetEntryCreate] = []


class ReceiptCreate(BaseModel):
    financial_year_id: int
    office_id: int
    section_id: Optional[int] = None
    receipt_date: Optional[date] = None
    receipt_no: Optional[str] = None
    supplier_name: Optional[str] = None
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    lines: list[ReceiptLineCreate]


class ReceiptUpdate(BaseModel):
    financial_year_id: Optional[int] = None
    office_id: Optional[int] = None
    section_id: Optional[int] = None
    receipt_date: Optional[date] = None
    supplier_name: Optional[str] = None
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    lines: Optional[list[ReceiptLineCreate]] = None


class ReceiptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_no: str
    receipt_date: date
    financial_year_id: int
    office_id: int
    section_id: Optional[int] = None
    supplier_name: Optional[str] = None
    reference_no: Optional[str] = None
    status: TransactionStatus
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    posted_by_id: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[ReceiptLineRead] = []
