from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import AssetStatus, AssetMovementType


# --- Asset Detail Schemas ---

class AssetDetailBase(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    purchase_date: Optional[date] = None
    purchase_reference: Optional[str] = None
    purchase_value: Optional[float] = None
    warranty_expiry_date: Optional[date] = None
    technical_specifications: Optional[str] = None


class AssetDetailCreate(AssetDetailBase):
    pass


class AssetDetailUpdate(AssetDetailBase):
    pass


class AssetDetailRead(AssetDetailBase):
    id: int
    asset_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Asset Movement Schemas ---

class AssetMovementBase(BaseModel):
    movement_type: AssetMovementType
    from_office_id: Optional[int] = None
    from_section_id: Optional[int] = None
    to_office_id: Optional[int] = None
    to_section_id: Optional[int] = None
    reference_document: Optional[str] = None
    remarks: Optional[str] = None


class AssetMovementCreate(AssetMovementBase):
    asset_id: Optional[int] = None
    new_status: Optional[AssetStatus] = None


class AssetMovementRead(AssetMovementBase):
    id: int
    asset_id: int
    movement_date: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Asset Schemas ---

class AssetBase(BaseModel):
    asset_no: str
    item_id: int
    serial_no: Optional[str] = None
    office_id: int
    section_id: Optional[int] = None
    status: Optional[AssetStatus] = AssetStatus.IN_STORE
    remarks: Optional[str] = None


class AssetCreate(AssetBase):
    detail: Optional[AssetDetailCreate] = None


class AssetUpdate(BaseModel):
    asset_no: Optional[str] = None
    item_id: Optional[int] = None
    serial_no: Optional[str] = None
    office_id: Optional[int] = None
    section_id: Optional[int] = None
    status: Optional[AssetStatus] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None
    detail: Optional[AssetDetailUpdate] = None


class AssetRead(AssetBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    asset_detail: Optional[AssetDetailRead] = None

    model_config = ConfigDict(from_attributes=True)
