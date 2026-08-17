from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

class ItemBase(BaseModel):
    code: str
    name: str
    category_id: int
    unit_id: int
    is_temporary: bool = False
    specification: Optional[str] = None
    remarks: Optional[str] = None

class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category_id: Optional[int] = None
    unit_id: Optional[int] = None
    is_temporary: Optional[bool] = None
    specification: Optional[str] = None
    remarks: Optional[str] = None
    is_active: Optional[bool] = None


class ItemRead(ItemBase):
    id: int
    is_temporary: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)