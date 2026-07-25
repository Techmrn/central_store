from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates

from app.crud.category import get_all_categories

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