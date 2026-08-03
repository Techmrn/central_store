from datetime import datetime

from pydantic import BaseModel, ConfigDict

class RoleBase(BaseModel):
    code: str
    name: str
    description: str | None = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(RoleBase):
    code: str | None = None
    name: str | None = None
    description: str | None = None

class RoleRead(RoleBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
