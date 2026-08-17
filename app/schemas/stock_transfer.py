from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionStatus


class StockTransferLineAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_line_id: int
    asset_id: int


class StockTransferLineCreate(BaseModel):
    item_id: int
    unit_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    remarks: Optional[str] = None
    asset_ids: Optional[list[int]] = None


class StockTransferLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_id: int
    item_id: int
    unit_id: Optional[int] = None
    quantity: float
    remarks: Optional[str] = None
    assets: list[StockTransferLineAssetRead] = []


class StockTransferCreate(BaseModel):
    financial_year_id: int
    from_office_id: int
    from_section_id: Optional[int] = None
    to_office_id: int
    to_section_id: Optional[int] = None
    transfer_date: Optional[date] = None
    transfer_no: Optional[str] = None
    remarks: Optional[str] = None
    lines: list[StockTransferLineCreate]


class StockTransferUpdate(BaseModel):
    transfer_date: Optional[date] = None
    from_office_id: Optional[int] = None
    from_section_id: Optional[int] = None
    to_office_id: Optional[int] = None
    to_section_id: Optional[int] = None
    remarks: Optional[str] = None
    lines: Optional[list[StockTransferLineCreate]] = None


class StockTransferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_no: str
    transfer_date: date
    financial_year_id: int
    from_office_id: int
    from_section_id: Optional[int] = None
    to_office_id: int
    to_section_id: Optional[int] = None
    status: TransactionStatus
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    posted_by_id: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[StockTransferLineRead] = []
