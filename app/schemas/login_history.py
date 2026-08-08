from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead


class LoginHistoryBase(BaseModel):
    user_id: int
    login_time: datetime
    logout_time: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    status: str = "SUCCESS"


class LoginHistoryCreate(LoginHistoryBase):
    pass


class LoginHistoryUpdate(BaseModel):
    logout_time: Optional[datetime] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class LoginHistoryRead(LoginHistoryBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginHistoryDetail(LoginHistoryRead):
    user: Optional[UserRead] = None
