from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional


from app.core.db import get_db
from app.core.templates import templates

from app.crud.unit import (
    get_all_units,
    get_unit_by_id,
    create_unit,
    update_unit,
    delete_unit,
)
from app.schemas.unit import UnitCreate, UnitUpdate

router = APIRouter(
    prefix="/unit",
    tags=["Unit UI"],
)


# ---------------------------------------------------------
# Unit List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_units(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_units(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
    request=request,
    name="unit/list.html",
    context={
        "units": result["items"],
        "pagination": result,
        "search": search,
        "success": success,
        "error": error,

        "page_title": "Unit Master",
        "page_subtitle": "Create and manage item units",

        "new_button_text": "New Unit",
        "new_button_url": "/unit/new",

        "empty_title": "No Units Found",
        "empty_message": "No unit matches your search.",
        "empty_button_text": "Add Unit",
        "empty_button_url": "/unit/new",
    },
)

# ---------------------------------------------------------
# New Unit Form
# ---------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_unit(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="unit/form.html",
        context={
            "request": request,
            "page_title": "New Unit",
        },
    )

@router.post("/new")
def save_unit(
    request: Request,
    name: str = Form(...),
    symbol: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):
    unit = UnitCreate(
        name=name,
        symbol=symbol,
        description=description or None,
    )

    try:
        create_unit(db=db, unit=unit)

        return RedirectResponse(
            url="/unit/?success=Unit created successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="unit/form.html",
            context={
                "request": request,
                "page_title": "New Unit",
                "error": str(e),
                "unit": unit,
            },
        )

####### Unit Update router for UI ##############

#------Form to edit unit details and update the same in database

@router.get("/{unit_id}/edit")
def edit_unit(
    unit_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    unit = get_unit_by_id(db, unit_id)

    if not unit:
        raise HTTPException(
            status_code=404,
            detail="Unit not found."
        )

    return templates.TemplateResponse(
        request=request,
        name="unit/form.html",
        context={
            "request": request,
            "page_title": "Edit Unit",
            "unit": unit,
            "error": None,
            "is_edit": True,
        },
    )

#_-----------Post request to update the unit details in database

@router.post("/{unit_id}/edit")
def update_unit_ui(
    unit_id: int,
    request: Request,
    name: str = Form(...),
    symbol: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
):

    unit = UnitUpdate(
        name=name,
        symbol=symbol,
        description=description or None,
    )

    try:

        updated = update_unit(
            db=db,
            unit_id=unit_id,
            unit=unit,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Unit not found."
            )

        return RedirectResponse(
            url="/unit/?success=Unit updated successfully",
            status_code=303,
        )

    except ValueError as e:

        unit.id = unit_id

        return templates.TemplateResponse(
            request=request,
            name="unit/form.html",
            context={
                "request": request,
                "page_title": "Edit Unit",
                "unit": unit,
                "error": str(e),
                "is_edit": True,
            },
        )
#----------Delete unit router for UI --------------------

@router.post("/{unit_id}/delete")
def delete_unit_ui(
    unit_id: int,
    db: Session = Depends(get_db),
):
    unit = delete_unit(db, unit_id = unit_id)

    if unit is None:
        raise HTTPException(
            status_code=404,
            detail="Unit not found."
        )

    return RedirectResponse(
        url="/unit/?success=Unit deleted successfully",
        status_code=303,
    )


#-------------Table route for live search------------

@router.get("/table", response_class=HTMLResponse)
def unit_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_units(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="unit/table_container.html",
        context={
            "request": request,
            "units": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Units Found",
            "empty_message": "No units are available.",
            "empty_button_text": "Add Unit",
            "empty_button_url": "/unit/new",
        },
    )
    
    

