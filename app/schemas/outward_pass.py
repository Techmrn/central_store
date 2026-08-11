from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class OutwardPassCreate(BaseModel):
    issue_id: int
    purpose: str
    recipient_name: str
    destination: str
    pass_date: Optional[date] = None
    pass_no: Optional[str] = None
    vehicle_no: Optional[str] = None
    remarks: Optional[str] = None


class OutwardPassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    pass_no: str
    pass_date: date
    issue_id: int
    purpose: str
    recipient_name: str
    destination: str
    vehicle_no: Optional[str] = None
    remarks: Optional[str] = None
    created_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
