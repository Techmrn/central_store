from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    code: str
    username: str
    full_name: str
    designation: str | None = None
    office_id: int
    section_id: int | None = None
    email: EmailStr | None = None
    mobile: str | None = None
    remarks: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    code: str | None = None
    username: str | None = None
    password: str | None = None
    full_name: str | None = None
    designation: str | None = None
    office_id: int | None = None
    section_id: int | None = None
    email: EmailStr | None = None
    mobile: str | None = None
    remarks: str | None = None


class UserRead(UserBase):
    id: int
    last_login: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)