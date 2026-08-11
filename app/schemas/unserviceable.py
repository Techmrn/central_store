from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.enums import AssetStatus, UnserviceableStatus


class UnserviceableMaterialCreate(BaseModel):
    financial_year_id: int
    item_id: int
    office_id: int
    section_id: Optional[int] = None
    quantity: float = Field(..., gt=0, description="Quantity marked unserviceable")
    reason: str = Field(..., min_length=1, max_length=255, description="Reason for unserviceability")
    reference_no: Optional[str] = Field(None, max_length=100)
    remarks: Optional[str] = Field(None, max_length=500)


class UnserviceableMaterialStatusUpdate(BaseModel):
    status: UnserviceableStatus
    quantity: Optional[float] = Field(None, gt=0, description="Quantity affected by transition")
    remarks: Optional[str] = Field(None, max_length=500)


class UnserviceableMaterialRead(BaseModel):
    id: int
    financial_year_id: int
    item_id: int
    item_name: str
    item_code: str
    office_id: int
    office_name: str
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    quantity: float
    reason: str
    status: UnserviceableStatus
    date_reported: datetime
    reference_no: Optional[str] = None
    remarks: Optional[str] = None
    reported_by_id: Optional[int] = None
    reported_by_name: Optional[str] = None

    class Config:
        from_attributes = True


class AssetUnserviceableUpdate(BaseModel):
    status: AssetStatus
    reason: str = Field(..., min_length=1, max_length=255, description="Reason for status change")
    remarks: Optional[str] = Field(None, max_length=500)


class UnserviceableRegisterItem(BaseModel):
    id: int
    register_type: str  # "ASSET" or "MATERIAL"
    asset_id: Optional[int] = None
    asset_no: Optional[str] = None
    serial_no: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    item_id: int
    item_name: str
    item_code: str
    category_name: str
    unit_name: Optional[str] = None
    office_id: int
    office_name: str
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    quantity: float
    status: str
    date_reported: datetime
    reason: str
    remarks: Optional[str] = None
    reference_no: Optional[str] = None
    reported_by_name: Optional[str] = None
