from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.financial_year import (
    create_financial_year,
    get_all_financial_years,
    get_financial_year_by_id,
    update_financial_year,
    delete_financial_year,
)
from app.schemas.financial_year import (
    FinancialYearCreate,
    FinancialYearUpdate,
    FinancialYearRead,
)

router = APIRouter(
    prefix="/financial-years",
    tags=["Financial Years"],
)


@router.post("/", response_model=FinancialYearRead)
def add_financial_year(
    financial_year: FinancialYearCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_financial_year(db, financial_year)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.get("/", response_model=list[FinancialYearRead])
def get_financial_years(
    db: Session = Depends(get_db),
):
    return get_all_financial_years(db)


@router.get("/{financial_year_id}", response_model=FinancialYearRead)
def get_financial_year(
    financial_year_id: int,
    db: Session = Depends(get_db),
):
    financial_year = get_financial_year_by_id(
        db,
        financial_year_id,
    )

    if financial_year is None:
        raise HTTPException(
            status_code=404,
            detail="Financial Year not found.",
        )

    return financial_year


@router.put("/{financial_year_id}", response_model=FinancialYearRead)
def edit_financial_year(
    financial_year_id: int,
    financial_year: FinancialYearUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_financial_year(
            db,
            financial_year_id,
            financial_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.delete("/{financial_year_id}", response_model=FinancialYearRead)
def remove_financial_year(
    financial_year_id: int,
    db: Session = Depends(get_db),
):
    financial_year = delete_financial_year(
        db,
        financial_year_id,
    )

    if financial_year is None:
        raise HTTPException(
            status_code=404,
            detail="Financial Year not found.",
        )

    return financial_year