from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date

from app.core.db import get_db
from app.core.templates import templates

from app.crud.financial_year import (
    get_all_financial_years_paginated,
    get_financial_year_by_id,
    create_financial_year,
    update_financial_year,
    delete_financial_year,
)
from app.schemas.financial_year import FinancialYearCreate, FinancialYearUpdate

router = APIRouter(
    prefix="/financial-year",
    tags=["Financial Year UI"],
)


# ---------------------------------------------------------
# Financial Year List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_financial_years(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_financial_years_paginated(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="financial_year/list.html",
        context={
            "request": request,
            "financial_years": result["items"],
            "pagination": result,
            "search": search,
            "success": success,
            "error": error,

            "page_title": "Financial Year Master",
            "page_subtitle": "Create and manage financial years",

            "new_button_text": "New Financial Year",
            "new_button_url": "/financial-year/new",

            "empty_title": "No Financial Years Found",
            "empty_message": "No financial years match your search.",
            "empty_button_text": "Add Financial Year",
            "empty_button_url": "/financial-year/new",

            "module_name": "Financial Years",
        },
    )


# ---------------------------------------------------------
# New Financial Year Form
# ---------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_financial_year(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="financial_year/form.html",
        context={
            "request": request,
            "page_title": "New Financial Year",
        },
    )


@router.post("/new")
def save_financial_year(
    request: Request,
    start_date: date = Form(...),
    end_date: date = Form(...),
    db: Session = Depends(get_db),
):

    financial_year = FinancialYearCreate(
        start_date=start_date,
        end_date=end_date,
    )

    try:
        result = create_financial_year(db=db, financial_year=financial_year)
        if result is None:
            return templates.TemplateResponse(
                request=request,
                name="financial_year/form.html",
                context={
                    "request": request,
                    "page_title": "New Financial Year",
                    "error": "Financial year already exists for these dates.",
                },
            )

        return RedirectResponse(
            url="/financial-year/?success=Financial Year created successfully",
            status_code=303,
        )

    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="financial_year/form.html",
            context={
                "request": request,
                "page_title": "New Financial Year",
                "error": str(e),
            },
        )


# ---------------------------------------------------------
# Edit Financial Year
# ---------------------------------------------------------

@router.get(
    "/{financial_year_id}/edit",
    response_class=HTMLResponse,
)
def edit_financial_year_page(
    financial_year_id: int,
    request: Request,
    db: Session = Depends(get_db),
):

    financial_year = get_financial_year_by_id(db, financial_year_id)

    if not financial_year:
        raise HTTPException(status_code=404, detail="Financial Year not found")

    return templates.TemplateResponse(
        request=request,
        name="financial_year/form.html",
        context={
            "request": request,
            "page_title": "Edit Financial Year",
            "financial_year": financial_year,
            "financial_year_id": financial_year.id,
        },
    )


@router.post("/{financial_year_id}/edit")
def update_financial_year_route(
    financial_year_id: int,
    request: Request,
    start_date: date = Form(...),
    end_date: date = Form(...),
    is_current: bool = Form(False),
    is_closed: bool = Form(False),
    db: Session = Depends(get_db),
):

    financial_year = FinancialYearUpdate(
        start_date=start_date,
        end_date=end_date,
        is_current=is_current,
        is_closed=is_closed,
        is_active=True,
    )

    try:
        result = update_financial_year(
            db=db,
            financial_year_id=financial_year_id,
            financial_year=financial_year,
        )

        if result is None:
            raise HTTPException(status_code=404, detail="Financial Year not found")

        if result is False:
            return templates.TemplateResponse(
                request=request,
                name="financial_year/form.html",
                context={
                    "request": request,
                    "page_title": "Edit Financial Year",
                    "financial_year_id": financial_year_id,
                    "error": "Financial year already exists for these dates.",
                },
            )

        return RedirectResponse(
            url="/financial-year/?success=Financial Year updated successfully",
            status_code=303,
        )

    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="financial_year/form.html",
            context={
                "request": request,
                "page_title": "Edit Financial Year",
                "financial_year_id": financial_year_id,
                "error": str(e),
            },
        )


# ---------------------------------------------------------
# Delete Financial Year
# ---------------------------------------------------------

@router.post("/{financial_year_id}/delete")
def delete_financial_year_route(
    financial_year_id: int,
    db: Session = Depends(get_db),
):

    result = delete_financial_year(db, financial_year_id)

    if not result:
        return RedirectResponse(
            url="/financial-year/?error=Financial Year not found",
            status_code=303,
        )

    return RedirectResponse(
        url="/financial-year/?success=Financial Year deleted successfully",
        status_code=303,
    )


# ---------------------------------------------------------
# Table (AJAX)
# ---------------------------------------------------------

@router.get(
    "/table",
    response_class=HTMLResponse,
)
def financial_year_table(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
):

    result = get_all_financial_years_paginated(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="financial_year/table_container.html",
        context={
            "request": request,
            "financial_years": result["items"],
            "pagination": result,
            "search": search,

            "module_name": "Financial Years",

            "empty_title": "No Financial Years Found",
            "empty_message": "No financial years are available.",
            "empty_button_text": "Add Financial Year",
            "empty_button_url": "/financial-year/new",
        },
    )