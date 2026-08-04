from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------
# Base
# ---------------------------------------------------------

class PermissionBase(BaseModel):
    module: str
    action: str
    description: Optional[str] = None


# ---------------------------------------------------------
# Create
# ---------------------------------------------------------

class PermissionCreate(PermissionBase):
    pass


# ---------------------------------------------------------
# Update
# ---------------------------------------------------------

class PermissionUpdate(BaseModel):
    module: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------
# Read
# ---------------------------------------------------------

class PermissionRead(BaseModel):
    id: int
    code: str
    module: str
    action: str
    name: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)