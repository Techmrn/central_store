from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional


from app.core.db import get_db
from app.core.templates import templates
from app.models.office import OfficeType

from app.crud.office import (
    get_all_offices,
    get_office_by_id,
    create_office,
    update_office,
    delete_office,
)
from app.schemas.office import OfficeCreate, OfficeUpdate

router = APIRouter(
    prefix="/office",
    tags=["Office UI"],
)


# ---------------------------------------------------------
# Office List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_offices(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_offices(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
    request=request,
    name="office/list.html",
    context={
        "offices": result["items"],
        "pagination": result,
        "search": search,
        "success": success,
        "error": error,

        "page_title": "Office Master",
        "page_subtitle": "Create and manage item offices",

        "new_button_text": "New Office",
        "new_button_url": "/office/new",

        "empty_title": "No Offices Found",
        "empty_message": "No office matches your search.",
        "empty_button_text": "Add Office",
        "empty_button_url": "/office/new",
    },
)

# ---------------------------------------------------------
# New Office Form
# ---------------------------------------------------------

@router.get(
    "/new",
    response_class=HTMLResponse,
)
def new_office(
    request: Request,
):

    return templates.TemplateResponse(
        request=request,
        name="office/form.html",
        context={
            "request": request,
            "page_title": "New Office",
        },
    )

@router.post("/new")
def save_office(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    office_type: OfficeType = Form(...),
    display_order: int = Form(...),
    remarks: str = Form(...),
    db: Session = Depends(get_db),
):
    office = OfficeCreate(
        code=code,
        name=name,
        office_type=office_type,
        display_order=display_order,
        remarks=remarks,
    )

    try:
        create_office(db=db, office=office)

        return RedirectResponse(
            url="/office/?success=Office created successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="office/form.html",
            context={
                "request": request,
                "page_title": "New Office",
                "error": str(e),
                "office": office,
            },
        )

####### Office Update router for UI ##############

#------Form to edit office details and update the same in database

@router.get("/{office_id}/edit")
def edit_office(
    office_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    office = get_office_by_id(db, office_id)

    if not office:
        raise HTTPException(
            status_code=404,
            detail="Office not found."
        )

    return templates.TemplateResponse(
        request=request,
        name="office/form.html",
        context={
            "request": request,
            "page_title": "Edit Office",
            "office": office,
            "office_id": office.id,
            "error": None,
            "is_edit": True,
        },
    )

#_-----------Post request to update the office details in database

@router.post("/{office_id}/edit")
def update_office_ui(
    office_id: int,
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    office_type: OfficeType = Form(...),
    display_order: int = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
):

    office = OfficeUpdate(
        code=code,
        name=name,
        office_type=office_type,
        display_order=display_order,
        remarks=remarks,
    )

    try:

        updated = update_office(
            db=db,
            office_id=office_id,
            office=office,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Office not found."
            )

        return RedirectResponse(
            url="/office/?success=Office updated successfully",
            status_code=303,
        )

    except ValueError as e:


        return templates.TemplateResponse(
            request=request,
            name="office/form.html",
            context={
                "request": request,
                "page_title": "Edit Office",
                "office": office,
                "office_id": office_id,
                "error": str(e),
                "is_edit": True,
            },
        )
#----------Delete office router for UI --------------------

@router.post("/{office_id}/delete")
def delete_office_ui(
    office_id: int,
    db: Session = Depends(get_db),
):
    office = delete_office(db, office_id = office_id)

    if office is None:
        raise HTTPException(
            status_code=404,
            detail="Office not found."
        )

    return RedirectResponse(
        url="/office/?success=Office deleted successfully",
        status_code=303,
    )


#-------------Table route for live search------------

@router.get("/table", response_class=HTMLResponse)
def office_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_offices(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="office/table_container.html",
        context={
            "request": request,
            "offices": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Offices Found",
            "empty_message": "No offices are available.",
            "empty_button_text": "Add office",
            "empty_button_url": "/office/new",
        },
    )
    
    

