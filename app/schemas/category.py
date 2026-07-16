from pydantic import BaseModel, ConfigDict

from app.models.enums import Category_Type

class CategoryBase(BaseModel):
    name: str
    type: Category_Type

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(CategoryBase):
    pass

class CategoryRead(CategoryBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


    