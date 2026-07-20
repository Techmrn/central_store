from pydantic import BaseModel, ConfigDict
from datetime import datetime

class OfficeBase(BaseModel):
    code: str
    name: str
    office_type: str
    display_order: int = 0
    remarks: str | None = None

class OfficeCreate(OfficeBase):
    pass

class OfficeUpdate(OfficeBase):
    code: str | None = None
    name: str | None = None
    office_type: str | None = None
    display_order: int | None = None
    remarks: str | None = None

class OfficeRead(OfficeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
