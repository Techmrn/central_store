from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IndentStatus, RequestSource, FulfillmentType


# --- Indent Line Schemas ---

class IndentLineBase(BaseModel):
    item_id: int
    requested_quantity: float = Field(gt=0, description="Requested quantity must be strictly greater than 0")
    issued_quantity: Optional[float] = Field(default=0.0, ge=0, description="Issued quantity must be non-negative")
    fulfillment_type: FulfillmentType = FulfillmentType.STOCK
    remarks: Optional[str] = None


class IndentLineCreate(IndentLineBase):
    pass


class IndentLineUpdate(BaseModel):
    id: int
    issued_quantity: Optional[float] = Field(default=None, ge=0, description="Storekeeper can update issued quantity")
    fulfillment_type: Optional[FulfillmentType] = None
    remarks: Optional[str] = None


class IndentLineRead(BaseModel):
    id: int
    indent_id: int
    item_id: int
    requested_quantity: float
    issued_quantity: float
    fulfillment_type: FulfillmentType
    remarks: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Indent Header Schemas ---

class IndentBase(BaseModel):
    indent_no: str
    indent_date: date
    received_date: date
    financial_year_id: int
    office_id: int
    section_id: Optional[int] = None
    request_source: Optional[RequestSource] = RequestSource.PHYSICAL
    reference_no: Optional[str] = None
    remarks: Optional[str] = None


class IndentCreate(IndentBase):
    lines: list[IndentLineCreate] = Field(min_items=1, description="At least one line item is required")


class IndentUpdate(BaseModel):
    indent_no: Optional[str] = None
    indent_date: Optional[date] = None
    received_date: Optional[date] = None
    financial_year_id: Optional[int] = None
    office_id: Optional[int] = None
    section_id: Optional[int] = None
    request_source: Optional[RequestSource] = None
    reference_no: Optional[str] = None
    status: Optional[IndentStatus] = None
    remarks: Optional[str] = None
    lines: Optional[list[IndentLineUpdate]] = None


class IndentRead(IndentBase):
    id: int
    status: IndentStatus
    created_by_id: Optional[int] = None
    processed_by_id: Optional[int] = None
    processed_at: Optional[datetime] = None
    closed_by_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    lines: list[IndentLineRead] = []

    model_config = ConfigDict(from_attributes=True)


class IndentCloseResponse(BaseModel):
    id: int
    indent_no: str
    status: IndentStatus
    closed_by_id: Optional[int] = None
    closed_at: Optional[datetime] = None
    message: str = "Indent closed successfully."

    model_config = ConfigDict(from_attributes=True)
