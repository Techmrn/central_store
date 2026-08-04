from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.opening_stock import (
    create_opening_stock,
    get_all_opening_stocks,
    get_opening_stock_by_id,
    update_opening_stock,
    delete_opening_stock,
)

from app.schemas.common import PaginatedResponse
from app.schemas.opening_stock import (
    OpeningStockCreate,
    OpeningStockUpdate,
    OpeningStockRead,
)

router = APIRouter(
    prefix="/opening-stocks",
    tags=["Opening Stock"],
)


@router.post("/", response_model=OpeningStockRead)
def add_opening_stock(
    opening_stock: OpeningStockCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_opening_stock(
            db,
            opening_stock,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.get("/", response_model=PaginatedResponse[OpeningStockRead])
def get_opening_stocks(
    db: Session = Depends(get_db),
):
    return get_all_opening_stocks(db)


@router.get("/{opening_stock_id}", response_model=OpeningStockRead)
def get_opening_stock(
    opening_stock_id: int,
    db: Session = Depends(get_db),
):
    opening_stock = get_opening_stock_by_id(
        db,
        opening_stock_id,
    )

    if opening_stock is None:
        raise HTTPException(
            status_code=404,
            detail="Opening Stock not found.",
        )

    return opening_stock


@router.put("/{opening_stock_id}", response_model=OpeningStockRead)
def edit_opening_stock(
    opening_stock_id: int,
    opening_stock: OpeningStockUpdate,
    db: Session = Depends(get_db),
):
    try:
        opening_stock_db = update_opening_stock(
            db,
            opening_stock_id,
            opening_stock,
        )

        if opening_stock_db is None:
            raise HTTPException(
                status_code=404,
                detail="Opening Stock not found.",
            )

        return opening_stock_db

    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail=str(e),
        )


@router.delete("/{opening_stock_id}", response_model=OpeningStockRead)
def remove_opening_stock(
    opening_stock_id: int,
    db: Session = Depends(get_db),
):
    opening_stock = delete_opening_stock(
        db,
        opening_stock_id,
    )

    if opening_stock is None:
        raise HTTPException(
            status_code=404,
            detail="Opening Stock not found.",
        )

    return opening_stock