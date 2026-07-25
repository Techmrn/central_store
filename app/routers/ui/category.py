from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates

from app.crud.category import get_all_categories,create_category
from app.schemas.category import CategoryCreate
from app.models.enums import Category_Type

router = APIRouter(
    prefix="/category",
    tags=["Category UI"],
)


# ---------------------------------------------------------
# Category List
# ---------------------------------------------------------

@router.get(
    "/",
    response_class=HTMLResponse,
)
def list_categories(
    request: Request,
    db: Session = Depends(get_db),
):

    categories = get_all_categories(db)

    return templates.TemplateResponse(
        request=request,
        name="category/list.html",
        context={
            "request": request,
            "page_title": "Category Master",
            "categories": categories,
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
            url="/category/",
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


