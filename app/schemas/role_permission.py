from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.role import RoleRead
from app.schemas.permission import PermissionRead


class RolePermissionBase(BaseModel):
    role_id: int
    permission_id: int


class RolePermissionCreate(RolePermissionBase):
    pass


class RolePermissionUpdate(BaseModel):
    role_id: Optional[int] = None
    permission_id: Optional[int] = None
    is_active: Optional[bool] = None


class RolePermissionRead(RolePermissionBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RolePermissionDetail(RolePermissionRead):
    role: Optional[RoleRead] = None
    permission: Optional[PermissionRead] = None


class RolePermissionBulkAssign(BaseModel):
    role_id: int
    permission_ids: list[int]
