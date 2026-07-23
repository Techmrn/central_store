from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class FinancialYearBase(BaseModel):
    year_name: str
    start_date: date
    end_date: date


class FinancialYearCreate(FinancialYearBase):
    pass


class FinancialYearUpdate(FinancialYearBase):
    is_current: bool
    is_closed: bool
    is_active: bool


class FinancialYearRead(FinancialYearBase):
    id: int
    is_current: bool
    is_closed: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)