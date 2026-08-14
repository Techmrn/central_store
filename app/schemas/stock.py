from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.models.enums import AssetStatus, MovementType, TransactionSource


class StockBalanceRead(BaseModel):
    item_id: int
    item_name: str
    item_code: str
    category_name: str
    unit_name: Optional[str] = None
    office_id: Optional[int] = None
    office_name: Optional[str] = None
    current_stock: float
    unserviceable_stock: float = 0.0
    usable_stock: float = 0.0



class StockMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    financial_year_id: int
    item_id: int
    office_id: int
    section_id: Optional[int] = None
    movement_type: MovementType
    transaction_source: TransactionSource
    quantity_in: float
    quantity_out: float
    movement_date: datetime
    reference_type: str
    reference_id: int
    reference_no: Optional[str] = None
    remarks: Optional[str] = None


class DistributionRegisterItem(BaseModel):
    issue_id: int
    issue_no: str
    issue_date: date
    financial_year_id: int
    financial_year_code: str
    office_id: int
    office_name: str
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    indent_id: int
    indent_no: str
    item_id: int
    item_name: str
    item_code: str
    quantity: float
    unit_name: Optional[str] = None
    remarks: Optional[str] = None


class ItemTransactionRegisterItem(BaseModel):
    movement_id: int
    movement_date: datetime
    financial_year_code: str
    indent_no: Optional[str] = None
    reference_type: str
    reference_no: Optional[str] = None
    movement_type: MovementType
    quantity_in: float
    quantity_out: float
    running_balance: float
    office_name: Optional[str] = None
    section_name: Optional[str] = None
    remarks: Optional[str] = None


class AssetRegisterItem(BaseModel):
    asset_id: int
    asset_no: str
    item_id: int
    item_name: str
    category_name: str
    serial_no: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    office_id: int
    office_name: str
    section_id: Optional[int] = None
    section_name: Optional[str] = None
    status: AssetStatus
    remarks: Optional[str] = None
