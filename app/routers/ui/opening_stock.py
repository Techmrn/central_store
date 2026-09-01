import math
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.core.constants import PAGE_SIZE
from app.dependencies.ui_auth import get_current_user_ui
from app.models.category import Category
from app.models.enums import Category_Type
from app.models.user import User
from app.models.item import Item

from app.crud.opening_stock import (
    create_opening_stock,
    get_all_opening_stocks,
    get_opening_stock_by_id,
    update_opening_stock,
    delete_opening_stock,
)

from app.crud.financial_year import get_all_financial_years

from app.schemas.opening_stock import (
    OpeningStockCreate,
    OpeningStockUpdate,
)

router = APIRouter(
    prefix="/opening-stock",
    tags=["Opening Stock UI"],
)


def _filter_and_paginate_opening_stocks(
    opening_stocks: list,
    search: str = "",
    page: int = 1,
):
    if search:
        search_lower = search.strip().lower()
        filtered = []
        for stock in opening_stocks:
            item_name = stock.item.name.lower() if stock.item and stock.item.name else ""
            item_code = stock.item.code.lower() if stock.item and stock.item.code else ""
            year_name = stock.financial_year.year_name.lower() if stock.financial_year and stock.financial_year.year_name else ""
            office_name = stock.office.name.lower() if stock.office and stock.office.name else ""
            remarks = stock.remarks.lower() if stock.remarks else ""
            if (
                search_lower in item_name
                or search_lower in item_code
                or search_lower in year_name
                or search_lower in office_name
                or search_lower in remarks
            ):
                filtered.append(stock)
    else:
        filtered = opening_stocks

    total_records = len(filtered)
    total_pages = math.ceil(total_records / PAGE_SIZE) if total_records else 1
    page = max(1, min(page, total_pages)) if total_records > 0 else 1
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    paginated_items = filtered[start_idx:end_idx]

    return {
        "items": paginated_items,
        "current_page": page,
        "page_size": PAGE_SIZE,
        "total_records": total_records,
        "total_pages": total_pages,
    }


# ---------------------------------------------------------
# Opening Stock List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_opening_stocks(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    all_stocks = get_all_opening_stocks(db)
    result = _filter_and_paginate_opening_stocks(all_stocks, search=search, page=page)

    return templates.TemplateResponse(
        request=request,
        name="opening_stock/list.html",
        context={
            "request": request,
            "opening_stocks": result["items"],
            "pagination": result,
            "search": search,
            "success": success,
            "error": error,
            "module_name": "Opening Stock",
            "page_title": "Opening Stock",
            "page_subtitle": "Create and manage inventory opening stock",
            "new_button_text": "New Opening Stock",
            "new_button_url": "/opening-stock/new",
            "empty_title": "No Opening Stock Found",
            "empty_message": "No opening stock matches your search.",
            "empty_button_text": "Add Opening Stock",
            "empty_button_url": "/opening-stock/new",
            "current_user": current_user,
        },
    )


# ---------------------------------------------------------
# Opening Stock Table (AJAX / Live Search)
# ---------------------------------------------------------

@router.get("/table", response_class=HTMLResponse)
def opening_stock_table(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    all_stocks = get_all_opening_stocks(db)
    result = _filter_and_paginate_opening_stocks(all_stocks, search=search, page=page)

    return templates.TemplateResponse(
        request=request,
        name="opening_stock/table_container.html",
        context={
            "request": request,
            "opening_stocks": result["items"],
            "pagination": result,
            "search": search,
            "module_name": "Opening Stock",
            "empty_title": "No Opening Stock Found",
            "empty_message": "No opening stock records are available.",
            "empty_button_text": "Add Opening Stock",
            "empty_button_url": "/opening-stock/new",
            "current_user": current_user,
        },
    )


# ---------------------------------------------------------
# New Opening Stock Form
# ---------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
def new_opening_stock(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    financial_years = get_all_financial_years(db)
    items = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.is_active == True,
            Category.is_active == True,
            Category.type == Category_Type.MATERIAL,
        )
        .order_by(Item.name)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="opening_stock/form.html",
        context={
            "request": request,
            "page_title": "New Opening Stock",
            "financial_years": financial_years,
            "items": items,
            "current_user": current_user,
        },
    )


@router.post("/new")
def save_opening_stock(
    request: Request,
    financial_year_id: int = Form(...),
    item_id: int = Form(...),
    quantity: Decimal = Form(...),
    unit_rate: Decimal = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    opening_stock = OpeningStockCreate(
        financial_year_id=financial_year_id,
        office_id=current_user.office_id,
        item_id=item_id,
        quantity=quantity,
        unit_rate=unit_rate,
        remarks=remarks or None,
    )

    try:
        create_opening_stock(db=db, opening_stock=opening_stock)

        return RedirectResponse(
            url="/opening-stock/?success=Opening stock created successfully",
            status_code=303,
        )

    except ValueError as e:
        financial_years = get_all_financial_years(db)
        items = (
            db.query(Item)
            .join(Category, Item.category_id == Category.id)
            .filter(
                Item.is_active == True,
                Category.is_active == True,
                Category.type == Category_Type.MATERIAL,
            )
            .order_by(Item.name)
            .all()
        )

        return templates.TemplateResponse(
            request=request,
            name="opening_stock/form.html",
            context={
                "request": request,
                "page_title": "New Opening Stock",
                "opening_stock": opening_stock,
                "financial_years": financial_years,
                "items": items,
                "current_user": current_user,
                "error": str(e),
            },
        )


# ---------------------------------------------------------
# Edit Opening Stock
# ---------------------------------------------------------

@router.get("/{opening_stock_id}/edit", response_class=HTMLResponse)
def edit_opening_stock(
    opening_stock_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    opening_stock = get_opening_stock_by_id(db, opening_stock_id)

    if not opening_stock:
        raise HTTPException(status_code=404, detail="Opening stock not found")

    financial_years = get_all_financial_years(db)
    items = (
        db.query(Item)
        .join(Category, Item.category_id == Category.id)
        .filter(
            Item.is_active == True,
            Category.is_active == True,
            Category.type == Category_Type.MATERIAL,
        )
        .order_by(Item.name)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="opening_stock/form.html",
        context={
            "request": request,
            "page_title": "Edit Opening Stock",
            "opening_stock": opening_stock,
            "opening_stock_id": opening_stock.id,
            "financial_years": financial_years,
            "items": items,
            "current_user": current_user,
            "is_edit": True,
        },
    )


# ---------------------------------------------------------
# Update Opening Stock
# ---------------------------------------------------------

@router.post("/{opening_stock_id}/edit")
def update_opening_stock_route(
    opening_stock_id: int,
    request: Request,
    financial_year_id: int = Form(...),
    item_id: int = Form(...),
    quantity: Decimal = Form(...),
    unit_rate: Decimal = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    opening_stock = OpeningStockUpdate(
        financial_year_id=financial_year_id,
        office_id=current_user.office_id,
        item_id=item_id,
        quantity=quantity,
        unit_rate=unit_rate,
        remarks=remarks or None,
    )

    try:
        result = update_opening_stock(
            db=db,
            opening_stock_id=opening_stock_id,
            opening_stock=opening_stock,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Opening stock not found")

        return RedirectResponse(
            url="/opening-stock/?success=Opening stock updated successfully",
            status_code=303,
        )

    except ValueError as e:
        financial_years = get_all_financial_years(db)
        items = (
            db.query(Item)
            .join(Category, Item.category_id == Category.id)
            .filter(
                Item.is_active == True,
                Category.is_active == True,
                Category.type == Category_Type.MATERIAL,
            )
            .order_by(Item.name)
            .all()
        )

        return templates.TemplateResponse(
            request=request,
            name="opening_stock/form.html",
            context={
                "request": request,
                "page_title": "Edit Opening Stock",
                "opening_stock": opening_stock,
                "opening_stock_id": opening_stock_id,
                "financial_years": financial_years,
                "items": items,
                "current_user": current_user,
                "error": str(e),
                "is_edit": True,
            },
        )


# ---------------------------------------------------------
# Delete Opening Stock
# ---------------------------------------------------------

@router.post("/{opening_stock_id}/delete")
def delete_opening_stock_route(
    opening_stock_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_ui),
):
    result = delete_opening_stock(db, opening_stock_id)

    if not result:
        return RedirectResponse(
            url="/opening-stock/?error=Opening stock not found",
            status_code=303,
        )

    return RedirectResponse(
        url="/opening-stock/?success=Opening stock deleted successfully",
        status_code=303,
    )
