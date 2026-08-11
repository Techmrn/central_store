from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.stock_return import (
    create_return,
    get_all_returns,
    get_return_by_id,
    update_return,
)
from app.dependencies.permissions import require_permission
from app.models.enums import TransactionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.stock_return import (
    StockReturnCreate,
    StockReturnRead,
    StockReturnUpdate,
)
from app.services.posting_service import post_return

router = APIRouter(
    prefix="/returns",
    tags=["Stock Returns"],
)


def _handle_value_error(e: ValueError):
    msg = str(e)
    if "already exists" in msg.lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
    elif "not found" in msg.lower():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)


@router.post(
    "/",
    response_model=StockReturnRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Stock Return",
)
def add_return(
    return_in: StockReturnCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RETURN_CREATE")),
):
    try:
        return create_return(db=db, return_in=return_in, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[StockReturnRead],
    summary="Get All Stock Returns",
)
def get_returns(
    search: str = "",
    return_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    transaction_status: Optional[TransactionStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RETURN_VIEW")),
):
    return get_all_returns(
        db=db,
        search=search,
        return_no=return_no,
        financial_year_id=financial_year_id,
        office_id=office_id,
        status=transaction_status,
        page=page,
    )


@router.get(
    "/{return_id}",
    response_model=StockReturnRead,
    summary="Get Return By ID",
)
def get_return(
    return_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RETURN_VIEW")),
):
    ret = get_return_by_id(db, return_id)
    if not ret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")
    return ret


@router.put(
    "/{return_id}",
    response_model=StockReturnRead,
    summary="Update Return",
)
def edit_return(
    return_id: int,
    return_in: StockReturnUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RETURN_CREATE")),
):
    try:
        return update_return(db=db, return_id=return_id, return_in=return_in)
    except ValueError as e:
        _handle_value_error(e)


@router.post(
    "/{return_id}/post",
    response_model=StockReturnRead,
    summary="Post Return Document",
)
def post_return_endpoint(
    return_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RETURN_POST")),
):
    try:
        return post_return(db=db, return_id=return_id, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)
