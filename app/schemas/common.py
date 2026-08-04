# for fixing the error in apis after added pagination for UI apis (CRUD folder)

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    current_page: int
    page_size: int
    total_records: int
    total_pages: int

    model_config = {
        "from_attributes": True,
    }