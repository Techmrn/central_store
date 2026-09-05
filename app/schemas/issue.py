from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DestinationType, TransactionStatus
from app.schemas.petty_purchase import PettyPurchaseCreate


class IssueLineAssetCreate(BaseModel):
    asset_id: int


class IssueLineAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_line_id: int
    asset_id: int


class IssueLineCreate(BaseModel):
    item_id: int
    unit_id: Optional[int] = None
    quantity: float = Field(..., gt=0)
    remarks: Optional[str] = None
    asset_ids: Optional[list[int]] = None
    petty_purchase: Optional[PettyPurchaseCreate] = None


class IssueLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    item_id: int
    unit_id: Optional[int] = None
    quantity: float
    remarks: Optional[str] = None
    assets: list[IssueLineAssetRead] = []


class IssueCreate(BaseModel):
    financial_year_id: int
    indent_id: int
    office_id: int
    section_id: Optional[int] = None
    destination_type: DestinationType = DestinationType.INTERNAL
    issue_date: Optional[date] = None
    issue_no: Optional[str] = None
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    lines: list[IssueLineCreate]


class IssueUpdate(BaseModel):
    office_id: Optional[int] = None
    section_id: Optional[int] = None
    destination_type: Optional[DestinationType] = None
    issue_date: Optional[date] = None
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    lines: Optional[list[IssueLineCreate]] = None


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_no: str
    issue_date: date
    financial_year_id: int
    indent_id: int
    office_id: int
    section_id: Optional[int] = None
    destination_type: DestinationType
    status: TransactionStatus
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    posted_by_id: Optional[int] = None
    posted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    lines: list[IssueLineRead] = []
