from datetime import datetime
from pydantic import BaseModel, ConfigDict

class SectionBase(BaseModel):
    office_id: int
    code: str
    name: str
    remarks: str | None = None

class SectionCreate(SectionBase):
    pass 

class SectionUpdate(BaseModel):
    office_id: int | None=None
    code: str | None = None
    name: str | None = None
    remarks: str | None = None

class SectionRead(SectionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    

