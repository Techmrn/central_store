"""
UI Router for Stock Registers.
All register pages use existing CRUD/service functions — no new tables.
"""
from datetime import date
from typing import Optional, Union
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.financial_year import get_all_financial_years, get_current_financial_year
from app.crud.office import get_all_offices_dropdown
from app.crud.section import get_all_sections_dropdown
from app.crud.stock import (
    get_asset_register_report,
    get_computer_register_report,
    get_distribution_register,
    get_ewaste_register_report,
    get_item_transaction_register,
    get_stock_balances,
)
from app.crud.unserviceable import get_unserviceable_register_report
from app.dependencies.ui_auth import get_current_user_ui
from app.models.category import Category
from app.models.enums import AssetStatus
from app.models.item import Item
from app.models.user import User

router = APIRouter(tags=["Stock Registers UI"])


def parse_int(val: Optional[Union[str, int]]) -> Optional[int]:
    """Safely parse query parameter to integer, treating empty strings as None."""
    if val is None or val == "" or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


# ──────────────────────────────────────────────────────────────────
# 1. CURRENT STOCK REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/stock-register", response_class=HTMLResponse)
def stock_register_ui(
    request: Request,
    search: str = "",
    category_id: Optional[str] = None,
    office_id: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    c_id = parse_int(category_id)
    o_id = parse_int(office_id)
    fy_id = parse_int(financial_year_id)

    data = get_stock_balances(
        db=db,
        search=search,
        category_id=c_id,
        office_id=o_id,
        financial_year_id=fy_id,
        page=page,
    )
    offices = get_all_offices_dropdown(db)
    financial_years = get_all_financial_years(db)
    categories = db.query(Category).filter(Category.is_active == True).order_by(Category.name).all()

    return templates.TemplateResponse(
        request=request,
        name="stock/register.html",
        context={
            "request": request,
            "page_title": "Current Stock Register",
            "user": current_user,
            "current_user": current_user,
            "items": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "financial_years": financial_years,
            "categories": categories,
            "search": search or "",
            "office_id_filter": o_id,
            "category_id_filter": c_id,
            "financial_year_id_filter": fy_id,
        },
    )


# ──────────────────────────────────────────────────────────────────
# 2. ITEM TRANSACTION REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/item-transaction-register", response_class=HTMLResponse)
def item_transaction_register_ui(
    request: Request,
    item_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    financial_year_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    i_id = parse_int(item_id)
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)
    fy_id = parse_int(financial_year_id)

    data = {"items": [], "total_records": 0, "current_page": 1, "total_pages": 1}
    if i_id:
        data = get_item_transaction_register(
            db=db,
            item_id=i_id,
            office_id=o_id,
            section_id=s_id,
            financial_year_id=fy_id,
            page=page,
        )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    financial_years = get_all_financial_years(db)

    # Fetch items: if office selected, load officewise stock items; otherwise all items
    if o_id:
        from app.models.opening_stock import OpeningStock
        from app.models.stock_movement import StockMovement
        op_sub = db.query(OpeningStock.item_id).filter(OpeningStock.office_id == o_id, OpeningStock.is_active == True)
        sm_sub = db.query(StockMovement.item_id).filter(StockMovement.office_id == o_id, StockMovement.is_active == True)
        if fy_id:
            op_sub = op_sub.filter(OpeningStock.financial_year_id == fy_id)
            sm_sub = sm_sub.filter(StockMovement.financial_year_id == fy_id)
        office_item_ids = op_sub.union(sm_sub)
        items = (
            db.query(Item)
            .filter(Item.id.in_(office_item_ids), Item.is_active == True)
            .order_by(Item.name)
            .all()
        )
    else:
        items = db.query(Item).filter(Item.is_active == True).order_by(Item.name).all()


    return templates.TemplateResponse(
        request=request,
        name="stock/item_transaction.html",
        context={
            "request": request,
            "page_title": "Item Transaction Register",
            "user": current_user,
            "current_user": current_user,
            "movements": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "items": items,
            "item_id_filter": i_id,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "financial_year_id_filter": fy_id,
        },
    )


# ──────────────────────────────────────────────────────────────────
# 3. DISTRIBUTION REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/distribution-register", response_class=HTMLResponse)
def distribution_register_ui(
    request: Request,
    financial_year_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    item_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    fy_id = parse_int(financial_year_id)
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)
    i_id = parse_int(item_id)

    f_date = None
    t_date = None
    if from_date and from_date.strip():
        try:
            f_date = date.fromisoformat(from_date.strip())
        except ValueError:
            f_date = None
    if to_date and to_date.strip():
        try:
            t_date = date.fromisoformat(to_date.strip())
        except ValueError:
            t_date = None

    data = get_distribution_register(
        db=db,
        financial_year_id=fy_id,
        office_id=o_id,
        section_id=s_id,
        item_id=i_id,
        from_date=f_date,
        to_date=t_date,
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    financial_years = get_all_financial_years(db)
    items = db.query(Item).filter(Item.is_active == True).order_by(Item.name).all()

    return templates.TemplateResponse(
        request=request,
        name="stock/distribution.html",
        context={
            "request": request,
            "page_title": "Distribution Register",
            "user": current_user,
            "current_user": current_user,
            "issues": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "sections": sections,
            "financial_years": financial_years,
            "items": items,
            "financial_year_id_filter": fy_id,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "item_id_filter": i_id,
            "from_date_filter": from_date or "",
            "to_date_filter": to_date or "",
        },
    )


# ──────────────────────────────────────────────────────────────────
# 4. ASSET REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/asset-register", response_class=HTMLResponse)
def asset_register_ui(
    request: Request,
    item_id: Optional[str] = None,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    asset_status: Optional[str] = None,
    search: str = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    i_id = parse_int(item_id)
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)

    status_enum = None
    if asset_status and asset_status.strip():
        try:
            status_enum = AssetStatus(asset_status.strip())
        except ValueError:
            status_enum = None

    data = get_asset_register_report(
        db=db,
        item_id=i_id,
        office_id=o_id,
        section_id=s_id,
        status=status_enum,
        search=search or "",
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)
    items = db.query(Item).filter(Item.is_active == True).order_by(Item.name).all()

    return templates.TemplateResponse(
        request=request,
        name="stock/asset_register.html",
        context={
            "request": request,
            "page_title": "Asset Register",
            "user": current_user,
            "current_user": current_user,
            "assets": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "sections": sections,
            "items": items,
            "asset_statuses": [s.value for s in AssetStatus],
            "item_id_filter": i_id,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "asset_status_filter": asset_status or "",
            "search": search or "",
        },
    )


# ──────────────────────────────────────────────────────────────────
# 5. COMPUTER REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/computer-register", response_class=HTMLResponse)
def computer_register_ui(
    request: Request,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    search: str = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)

    data = get_computer_register_report(
        db=db,
        office_id=o_id,
        section_id=s_id,
        search=search or "",
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)

    return templates.TemplateResponse(
        request=request,
        name="stock/computer_register.html",
        context={
            "request": request,
            "page_title": "Computer Register",
            "user": current_user,
            "current_user": current_user,
            "assets": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "sections": sections,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "search": search or "",
        },
    )


# ──────────────────────────────────────────────────────────────────
# 6. E-WASTE REGISTER
# ──────────────────────────────────────────────────────────────────
@router.get("/ewaste-register", response_class=HTMLResponse)
def ewaste_register_ui(
    request: Request,
    office_id: Optional[str] = None,
    section_id: Optional[str] = None,
    search: str = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    o_id = parse_int(office_id)
    s_id = parse_int(section_id)

    data = get_ewaste_register_report(
        db=db,
        office_id=o_id,
        section_id=s_id,
        search=search or "",
        page=page,
    )

    offices = get_all_offices_dropdown(db)
    sections = get_all_sections_dropdown(db)

    return templates.TemplateResponse(
        request=request,
        name="stock/ewaste_register.html",
        context={
            "request": request,
            "page_title": "E-Waste Register",
            "user": current_user,
            "current_user": current_user,
            "assets": data.get("items", []),
            "total": data.get("total_records", 0),
            "page": data.get("current_page", 1),
            "total_pages": data.get("total_pages", 1),
            "offices": offices,
            "sections": sections,
            "office_id_filter": o_id,
            "section_id_filter": s_id,
            "search": search or "",
        },
    )
