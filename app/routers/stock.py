from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.crud.stock import (
    get_asset_register_report,
    get_computer_register_report,
    get_distribution_register,
    get_ewaste_register_report,
    get_item_transaction_register,
    get_office_stock_items,
    get_stock_balances,
    get_stock_ledger,
)
from app.crud.financial_year import get_current_financial_year
from app.dependencies.permissions import require_permission
from app.models.enums import AssetStatus
from app.schemas.common import PaginatedResponse
from app.schemas.stock import (
    AssetRegisterItem,
    DistributionRegisterItem,
    ItemTransactionRegisterItem,
    StockBalanceRead,
    StockMovementRead,
)
from app.schemas.unserviceable import UnserviceableRegisterItem


router = APIRouter(
    prefix="/stock",
    tags=["Stock & Registers"],
)


@router.get(
    "/balance",
    response_model=PaginatedResponse[StockBalanceRead],
    summary="Get Current Stock Balances",
)
def get_stock_balance_endpoint(
    search: str = "",
    category_id: Optional[int] = None,
    office_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_stock_balances(
        db=db,
        search=search,
        category_id=category_id,
        office_id=office_id,
        page=page,
    )


@router.get(
    "/ledger",
    response_model=PaginatedResponse[StockMovementRead],
    summary="Get Authoritative Stock Movement Ledger",
)
def get_stock_ledger_endpoint(
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    financial_year_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_stock_ledger(
        db=db,
        item_id=item_id,
        office_id=office_id,
        financial_year_id=financial_year_id,
        page=page,
    )


@router.get(
    "/distribution-register",
    response_model=PaginatedResponse[DistributionRegisterItem],
    summary="Get Distribution Register Report",
)
def get_distribution_register_endpoint(
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    item_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_distribution_register(
        db=db,
        financial_year_id=financial_year_id,
        office_id=office_id,
        section_id=section_id,
        item_id=item_id,
        page=page,
    )


@router.get(
    "/item-transaction-register",
    response_model=PaginatedResponse[ItemTransactionRegisterItem],
    summary="Get Item-Wise Transaction Register Report",
)
def get_item_transaction_register_endpoint(
    item_id: int,
    office_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_item_transaction_register(
        db=db,
        item_id=item_id,
        office_id=office_id,
        page=page,
    )


@router.get(
    "/asset-register",
    response_model=PaginatedResponse[AssetRegisterItem],
    summary="Get Asset Register Report",
)
def get_asset_register_endpoint(
    item_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    asset_status: Optional[AssetStatus] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_asset_register_report(
        db=db,
        item_id=item_id,
        office_id=office_id,
        section_id=section_id,
        status=asset_status,
        page=page,
    )


@router.get(
    "/computer-register",
    response_model=PaginatedResponse[AssetRegisterItem],
    summary="Get Computer Register Report",
)
def get_computer_register_endpoint(
    office_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_computer_register_report(
        db=db,
        office_id=office_id,
        page=page,
    )


@router.get(
    "/e-waste-register",
    response_model=PaginatedResponse[AssetRegisterItem],
    summary="Get E-Waste Register Report",
)
def get_ewaste_register_endpoint(
    office_id: Optional[int] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    return get_ewaste_register_report(
        db=db,
        office_id=office_id,
        page=page,
    )


@router.get(
    "/unserviceable-register",
    response_model=PaginatedResponse[UnserviceableRegisterItem],
    summary="Get Unserviceable Asset / Item Register Report",
)
def get_unserviceable_register_endpoint(
    financial_year_id: Optional[int] = None,
    office_id: Optional[int] = None,
    section_id: Optional[int] = None,
    item_id: Optional[int] = None,
    category_id: Optional[int] = None,
    asset_or_material: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("STOCK_VIEW")),
):
    from app.crud.unserviceable import get_unserviceable_register_report
    return get_unserviceable_register_report(
        db=db,
        financial_year_id=financial_year_id,
        office_id=office_id,
        section_id=section_id,
        item_id=item_id,
        category_id=category_id,
        asset_or_material=asset_or_material,
        status_filter=status_filter,
        page=page,
    )


@router.get(
    "/office-items/{office_id}",
    summary="Get Items with Stock Identity for an Office (current FY)",
)
def get_office_items_endpoint(
    office_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns items that have a stock record (OpeningStock or StockMovement)
    for the selected office in the current financial year.
    Used by the Physical Indent entry form to populate the item dropdown.
    """
    fy = get_current_financial_year(db)
    fy_id = fy.id if fy else None
    items = get_office_stock_items(db=db, office_id=office_id, financial_year_id=fy_id)
    return items
