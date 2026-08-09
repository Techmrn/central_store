from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
from app.crud.financial_year import (
    create_financial_year,
    get_all_financial_years,
    get_financial_year_by_id,
    update_financial_year,
    delete_financial_year,
)

from app.schemas.common import PaginatedResponse
from app.schemas.financial_year import (
    FinancialYearCreate,
    FinancialYearUpdate,
    FinancialYearRead,
)

router = APIRouter(
    prefix="/financial-years",
    tags=["Financial Years"],
)


@router.post(
    "/",
    response_model=FinancialYearRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Financial Year",
)
def add_financial_year(
    financial_year: FinancialYearCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("FINANCIAL_YEAR_CREATE")),
):
    try:
        return create_financial_year(db, financial_year)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[FinancialYearRead],
    summary="Get All Financial Years",
)
def get_financial_years(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("FINANCIAL_YEAR_VIEW")),
):
    return get_all_financial_years(db)


@router.get(
    "/{financial_year_id}",
    response_model=FinancialYearRead,
    summary="Get Financial Year By ID",
)
def get_financial_year(
    financial_year_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("FINANCIAL_YEAR_VIEW")),
):
    financial_year = get_financial_year_by_id(
        db,
        financial_year_id,
    )

    if financial_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial Year not found.",
        )

    return financial_year


@router.put(
    "/{financial_year_id}",
    response_model=FinancialYearRead,
    summary="Update Financial Year",
)
def edit_financial_year(
    financial_year_id: int,
    financial_year: FinancialYearUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("FINANCIAL_YEAR_UPDATE")),
):
    try:
        return update_financial_year(
            db,
            financial_year_id,
            financial_year,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{financial_year_id}",
    response_model=FinancialYearRead,
    summary="Delete Financial Year",
)
def remove_financial_year(
    financial_year_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("FINANCIAL_YEAR_DELETE")),
):
    financial_year = delete_financial_year(
        db,
        financial_year_id,
    )

    if financial_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Financial Year not found.",
        )

    return financial_year