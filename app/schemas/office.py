from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.models.office import OfficeType

class OfficeBase(BaseModel):
    code: str
    name: str
    office_type: OfficeType
    display_order: int = 0
    remarks: str | None = None

class OfficeCreate(OfficeBase):
    pass

class OfficeUpdate(OfficeBase):
    code: str | None = None
    name: str | None = None
    office_type: OfficeType | None = None
    display_order: int | None = None
    remarks: str | None = None

class OfficeRead(OfficeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
