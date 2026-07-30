from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional


from app.core.db import get_db
from app.core.templates import templates

from app.crud.category import (
    get_all_categories,
    get_category_by_id,
    create_category,
    update_category,
    delete_category,
)
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.models.enums import Category_Type

router = APIRouter(
    prefix="/category",
    tags=["Category UI"],
)


# ---------------------------------------------------------
# Category List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_categories(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_categories(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
    request=request,
    name="category/list.html",
    context={
        "categories": result["items"],
        "pagination": result,
        "search": search,
        "success": success,
        "error": error,

        "page_title": "Category Master",
        "page_subtitle": "Create and manage item categories",

        "new_button_text": "New Category",
        "new_button_url": "/category/new",

        "empty_title": "No Categories Found",
        "empty_message": "No category matches your search.",
        "empty_button_text": "Add Category",
        "empty_button_url": "/category/new",
    },
)

# ---------------------------------------------------------
# New Category Form
# ---------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_category(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="category/form.html",
        context={
            "request": request,
            "page_title": "New Category",
        },
    )

@router.post("/new")
def save_category(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: Category_Type = Form(...),
    db: Session = Depends(get_db),
):
    category = CategoryCreate(
        code=code,name=name,type=type,
    )

    try:
        create_category(db=db, category=category)

        return RedirectResponse(
            url="/category/?success=Category created successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="category/form.html",
            context={
                "request": request,
                "page_title": "New Category",
                "error": str(e),
                "category": category,
            },
        )

####### Category Update router for UI ##############

#------Form to edit category details and update the same in database

@router.get("/{category_id}/edit")
def edit_category(
    category_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    category = get_category_by_id(db, category_id)

    if not category:
        raise HTTPException(
            status_code=404,
            detail="Category not found."
        )

    return templates.TemplateResponse(
        request=request,
        name="category/form.html",
        context={
            "request": request,
            "page_title": "Edit Category",
            "category": category,
            "category_id": category.id,
            "error": None,
            "is_edit": True,
        },
    )

#_-----------Post request to update the category details in database

@router.post("/{category_id}/edit")
def update_category_ui(
    category_id: int,
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: Category_Type = Form(...),
    db: Session = Depends(get_db),
):

    category = CategoryUpdate(
        code=code,
        name=name,
        type=type,
    )

    try:

        updated = update_category(
            db=db,
            category_id=category_id,
            category=category,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Category not found."
            )

        return RedirectResponse(
            url="/category/?success=Category updated successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="category/form.html",
            context={
                "request": request,
                "page_title": "Edit Category",
                "category": category,
                "category_id": category_id,
                "error": str(e),
                "is_edit": True,
            },
        )
#----------Delete category router for UI --------------------

@router.post("/{category_id}/delete")
def delete_category_ui(
    category_id: int,
    db: Session = Depends(get_db),
):
    category = delete_category(db, category_id = category_id)

    if category is None:
        raise HTTPException(
            status_code=404,
            detail="Category not found."
        )

    return RedirectResponse(
        url="/category/?success=Category deleted successfully",
        status_code=303,
    )


#-------------Table route for live search------------

@router.get("/table", response_class=HTMLResponse)
def category_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_categories(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="category/table_container.html",
        context={
            "request": request,
            "categories": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Categories Found",
            "empty_message": "No categories are available.",
            "empty_button_text": "Add Unit",
            "empty_button_url": "/unit/new",
        },
    )
    
    

