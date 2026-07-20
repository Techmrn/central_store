from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UnitBase(BaseModel):
    name: str
    symbol: str
    description : str | None = None

class UnitCreate(UnitBase):
    pass

class UnitUpdate(UnitBase):
    name: str | None = None
    symbol: str | None = None
    description : str | None = None

class UnitRead(UnitBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)