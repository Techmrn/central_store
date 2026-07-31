from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates

from app.crud.item import (
    get_all_items,
    get_item_by_id,
    create_item,
    update_item,
    delete_item,
)

from app.crud.category import get_category_lookup
from app.crud.unit import get_unit_lookup

from app.schemas.item import (
    ItemCreate,
    ItemUpdate,
)

router = APIRouter(
    prefix="/item",
    tags=["Item UI"],
)

# ---------------------------------------------------------
# Item List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_items(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_items(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="item/list.html",
        context={
            "request": request,
            "items": result["items"],
            "pagination": result,
            "search": search,
            "success": success,
            "error": error,
            "module_name": "Items",

            "page_title": "Item Master",
            "page_subtitle": "Create and manage inventory items",

            "new_button_text": "New Item",
            "new_button_url": "/item/new",

            "empty_title": "No Items Found",
            "empty_message": "No items match your search.",
            "empty_button_text": "Add Item",
            "empty_button_url": "/item/new",
        },
    )

# ---------------------------------------------------------
# New Item Form
# ---------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_item(
    request: Request,
    db: Session = Depends(get_db),
):

    categories = get_category_lookup(db)
    units = get_unit_lookup(db)

    return templates.TemplateResponse(
        request=request,
        name="item/form.html",
        context={
            "request": request,
            "page_title": "New Item",
            "categories": categories,
            "units": units,
        },
    )

@router.post("/new")
def save_item(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    unit_id: int = Form(...),
    specification: str = Form(""),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
):

    item = ItemCreate(
        code=code,
        name=name,
        category_id=category_id,
        unit_id=unit_id,
        specification=specification,
        remarks=remarks,
    )

    try:

        create_item(
            db=db,
            item=item,
        )

        return RedirectResponse(
            url="/item/?success=Item created successfully",
            status_code=303,
        )

    except ValueError as e:

        categories = get_category_lookup(db)
        units = get_unit_lookup(db)

        return templates.TemplateResponse(
            request=request,
            name="item/form.html",
            context={
                "request": request,
                "page_title": "New Item",
                "item": item,
                "categories": categories,
                "units": units,
                "error": str(e),
            },
        )

# ---------------------------------------------------------
# Edit Item
# ---------------------------------------------------------

@router.get(
    "/{item_id}/edit",
    response_class=HTMLResponse,
)
def edit_item(
    item_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    item = get_item_by_id(db, item_id)

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    categories = get_category_lookup(db)
    units = get_unit_lookup(db)

    return templates.TemplateResponse(
        request=request,
        name="item/form.html",
        context={
            "request": request,
            "page_title": "Edit Item",
            "item": item,
            "item_id": item.id,      # Important
            "categories": categories,
            "units": units,
        },
    )

# ---------------------------------------------------------
# Update Item
# ---------------------------------------------------------

@router.post("/{item_id}/edit")
def update_item_route(
    item_id: int,
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    category_id: int = Form(...),
    unit_id: int = Form(...),
    specification: str = Form(""),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
):

    item = ItemUpdate(
        code=code,
        name=name,
        category_id=category_id,
        unit_id=unit_id,
        specification=specification,
        remarks=remarks,
    )

    try:

        result = update_item(
            db=db,
            item_id=item_id,
            item=item,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Item not found")

        return RedirectResponse(
            url="/item/?success=Item updated successfully",
            status_code=303,
        )

    except ValueError as e:

        categories = get_category_lookup(db)
        units = get_unit_lookup(db)

        return templates.TemplateResponse(
            request=request,
            name="item/form.html",
            context={
                "request": request,
                "page_title": "Edit Item",
                "item": item,
                "item_id": item_id,   # Important
                "categories": categories,
                "units": units,
                "error": str(e),
            },
        )

# ---------------------------------------------------------
# Delete Item
# ---------------------------------------------------------

@router.post("/{item_id}/delete")
def delete_item_route(
    item_id: int,
    db: Session = Depends(get_db),
):

    result = delete_item(db, item_id)

    if not result:
        return RedirectResponse(
            url="/item/?error=Item not found",
            status_code=303,
        )

    return RedirectResponse(
        url="/item/?success=Item deleted successfully",
        status_code=303,
    )


# ---------------------------------------------------------
# Table (AJAX)
# ---------------------------------------------------------

@router.get(
    "/table",
    response_class=HTMLResponse,
)
def item_table(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
):

    result = get_all_items(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="item/table_container.html",
        context={
            "request": request,
            "items": result["items"],
            "pagination": result,
            "search": search,
            "module_name": "Items",
            "empty_title": "No Items Found",
            "empty_message": "No items are available.",
            "empty_button_text": "Add Item",
            "empty_button_url": "/item/new",
        },
    )

