from pydantic import BaseModel, ConfigDict
from datetime import datetime

from app.models.enums import Category_Type

class CategoryBase(BaseModel):
    name: str
    type: Category_Type

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    name: str | None = None
    type: Category_Type | None = None

class CategoryRead(CategoryBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


    