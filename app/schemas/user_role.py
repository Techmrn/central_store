from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.role import RoleRead
from app.schemas.user import UserRead


class UserRoleBase(BaseModel):
    user_id: int
    role_id: int


class UserRoleCreate(UserRoleBase):
    pass


class UserRoleUpdate(BaseModel):
    user_id: Optional[int] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserRoleRead(UserRoleBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserRoleDetail(UserRoleRead):
    user: Optional[UserRead] = None
    role: Optional[RoleRead] = None


class UserRoleBulkAssign(BaseModel):
    user_id: int
    role_ids: list[int]
