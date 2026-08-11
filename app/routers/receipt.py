from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.receipt import (
    create_receipt,
    delete_receipt,
    get_all_receipts,
    get_receipt_by_id,
    update_receipt,
)
from app.dependencies.permissions import require_permission
from app.models.enums import TransactionStatus
from app.schemas.common import PaginatedResponse
from app.schemas.receipt import (
    ReceiptCreate,
    ReceiptRead,
    ReceiptUpdate,
)
from app.services.posting_service import post_receipt

router = APIRouter(
    prefix="/receipts",
    tags=["Goods Receipts"],
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
    response_model=ReceiptRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Goods Receipt",
)
def add_receipt(
    receipt: ReceiptCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_CREATE")),
):
    try:
        return create_receipt(db=db, receipt_in=receipt, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)


@router.get(
    "/",
    response_model=PaginatedResponse[ReceiptRead],
    summary="Get All Receipts",
)
def get_receipts(
    search: str = "",
    receipt_no: Optional[str] = None,
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    transaction_status: Optional[TransactionStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_VIEW")),
):
    return get_all_receipts(
        db=db,
        search=search,
        receipt_no=receipt_no,
        financial_year_id=financial_year_id,
        office_id=office_id,
        status=transaction_status,
        page=page,
    )


@router.get(
    "/{receipt_id}",
    response_model=ReceiptRead,
    summary="Get Receipt By ID",
)
def get_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_VIEW")),
):
    receipt = get_receipt_by_id(db, receipt_id)
    if not receipt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found.")
    return receipt


@router.put(
    "/{receipt_id}",
    response_model=ReceiptRead,
    summary="Update Receipt",
)
def edit_receipt(
    receipt_id: int,
    receipt: ReceiptUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_UPDATE")),
):
    try:
        return update_receipt(db=db, receipt_id=receipt_id, receipt_in=receipt)
    except ValueError as e:
        _handle_value_error(e)


@router.delete(
    "/{receipt_id}",
    response_model=ReceiptRead,
    summary="Delete Receipt",
)
def remove_receipt(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_DELETE")),
):
    try:
        receipt = delete_receipt(db, receipt_id)
        if not receipt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found.")
        return receipt
    except ValueError as e:
        _handle_value_error(e)


@router.post(
    "/{receipt_id}/post",
    response_model=ReceiptRead,
    summary="Post Receipt Document",
)
def post_receipt_endpoint(
    receipt_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("RECEIPT_POST")),
):
    try:
        return post_receipt(db=db, receipt_id=receipt_id, user_id=current_user.id)
    except ValueError as e:
        _handle_value_error(e)
