from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class FinancialYearBase(BaseModel):
    start_date: date
    end_date: date
    year_name: str | None = None


class FinancialYearCreate(FinancialYearBase):
    pass


class FinancialYearUpdate(FinancialYearBase):
    is_current: bool = False
    is_closed: bool = False
    is_active: bool = True


class FinancialYearRead(FinancialYearBase):
    id: int
    year_name: str
    is_current: bool
    is_closed: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)