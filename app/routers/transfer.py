from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.stock_transfer import (
    create_transfer,
    get_all_transfers,
    get_transfer_by_id,
    update_transfer,
)
from app.dependencies.permissions import require_permission
from app.models.enums import TransactionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferRead,
    StockTransferUpdate,
)
from app.services.posting_service import post_transfer

router = APIRouter(
    prefix="/transfers",
    tags=["Stock Transfers"],
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
    response_model=StockTransferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Stock Transfer",
)
def add_transfer(
    transfer_in: StockTransferCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("TRANSFER_CREATE")),
):
    try:
        return create_transfer(db=db, transfer_in=transfer_in, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[StockTransferRead],
    summary="Get All Stock Transfers",
)
def get_transfers(
    search: str = "",
    transfer_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    from_office_id: Optional[int] = None,
    to_office_id: Optional[int] = None,
    transaction_status: Optional[TransactionStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("TRANSFER_VIEW")),
):
    return get_all_transfers(
        db=db,
        search=search,
        transfer_no=transfer_no,
        financial_year_id=financial_year_id,
        from_office_id=from_office_id,
        to_office_id=to_office_id,
        status=transaction_status,
        page=page,
    )


@router.get(
    "/{transfer_id}",
    response_model=StockTransferRead,
    summary="Get Transfer By ID",
)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("TRANSFER_VIEW")),
):
    trn = get_transfer_by_id(db, transfer_id)
    if not trn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found.")
    return trn


@router.put(
    "/{transfer_id}",
    response_model=StockTransferRead,
    summary="Update Transfer",
)
def edit_transfer(
    transfer_id: int,
    transfer_in: StockTransferUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("TRANSFER_CREATE")),
):
    try:
        return update_transfer(db=db, transfer_id=transfer_id, transfer_in=transfer_in)
    except ValueError as e:
        _handle_value_error(e)


@router.post(
    "/{transfer_id}/post",
    response_model=StockTransferRead,
    summary="Post Transfer Document",
)
def post_transfer_endpoint(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("TRANSFER_POST")),
):
    try:
        return post_transfer(db=db, transfer_id=transfer_id, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)
