from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TransactionStatus


class StockReturnLineAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_line_id: int
    asset_id: int


class StockReturnLineCreate(BaseModel):
    item_id: int
    unit_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    remarks: Optional[str] = None
    asset_ids: Optional[list[int]] = None


class StockReturnLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_id: int
    item_id: int
    unit_id: Optional[int] = None
    quantity: float
    remarks: Optional[str] = None
    assets: list[StockReturnLineAssetRead] = []


class StockReturnCreate(BaseModel):
    financial_year_id: int
    office_id: int
    section_id: Optional[int] = None
    return_date: Optional[date] = None
    return_no: Optional[str] = None
    reference_issue_id: Optional[int] = None
    remarks: Optional[str] = None
    lines: list[StockReturnLineCreate]


class StockReturnUpdate(BaseModel):
    reference_issue_id: Optional[int] = None
    remarks: Optional[str] = None
    lines: Optional[list[StockReturnLineCreate]] = None


class StockReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    return_no: str
    return_date: date
    financial_year_id: int
    office_id: int
    section_id: Optional[int] = None
    reference_issue_id: Optional[int] = None
    status: TransactionStatus
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    posted_by_id: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[StockReturnLineRead] = []
