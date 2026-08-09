from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
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


@router.post(
    "/",
    response_model=OpeningStockRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Opening Stock",
)
def add_opening_stock(
    opening_stock: OpeningStockCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OPENING_STOCK_CREATE")),
):
    try:
        return create_opening_stock(
            db,
            opening_stock,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[OpeningStockRead],
    summary="Get All Opening Stocks",
)
def get_opening_stocks(
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OPENING_STOCK_VIEW")),
):
    return get_all_opening_stocks(db)


@router.get(
    "/{opening_stock_id}",
    response_model=OpeningStockRead,
    summary="Get Opening Stock By ID",
)
def get_opening_stock(
    opening_stock_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OPENING_STOCK_VIEW")),
):
    opening_stock = get_opening_stock_by_id(
        db,
        opening_stock_id,
    )

    if opening_stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opening Stock not found.",
        )

    return opening_stock


@router.put(
    "/{opening_stock_id}",
    response_model=OpeningStockRead,
    summary="Update Opening Stock",
)
def edit_opening_stock(
    opening_stock_id: int,
    opening_stock: OpeningStockUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OPENING_STOCK_UPDATE")),
):
    try:
        opening_stock_db = update_opening_stock(
            db,
            opening_stock_id,
            opening_stock,
        )

        if opening_stock_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Opening Stock not found.",
            )

        return opening_stock_db

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{opening_stock_id}",
    response_model=OpeningStockRead,
    summary="Delete Opening Stock",
)
def remove_opening_stock(
    opening_stock_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("OPENING_STOCK_DELETE")),
):
    opening_stock = delete_opening_stock(
        db,
        opening_stock_id,
    )

    if opening_stock is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Opening Stock not found.",
        )

    return opening_stock