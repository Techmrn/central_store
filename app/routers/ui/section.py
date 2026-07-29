from fastapi import APIRouter, Depends, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional


from app.core.db import get_db
from app.core.templates import templates
from app.crud.office import get_all_offices # for foreign key

from app.crud.section import (
    get_all_sections,
    get_section_by_id,
    create_section,
    update_section,
    delete_section,
)
from app.schemas.sections import SectionCreate, SectionUpdate

router = APIRouter(
    prefix="/section",
    tags=["Section UI"],
)


# ---------------------------------------------------------
# Section List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_sections(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_sections(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
    request=request,
    name="section/list.html",
    context={
        "sections": result["items"],
        "pagination": result,
        "search": search,
        "success": success,
        "error": error,

        "page_title": "Section Master",
        "page_subtitle": "Create and manage item sections",

        "new_button_text": "New Section",
        "new_button_url": "/section/new",

        "empty_title": "No Sections Found",
        "empty_message": "No section matches your search.",
        "empty_button_text": "Add Section",
        "empty_button_url": "/section/new",
    },
)

# ---------------------------------------------------------
# New Section Form
# ---------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
def new_section(
    request: Request,
    db: Session = Depends(get_db),
):
    offices = get_all_offices(db=db)["items"]

    return templates.TemplateResponse(
        request=request,
        name="section/form.html",
        context={
            "request": request,
            "page_title": "New Section",
            "offices": offices,
        },
    )


@router.post("/new")
def save_section(
    request: Request,
    office_id: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
):

    section = SectionCreate(
        office_id=office_id,
        code=code,
        name=name,
        remarks=remarks,
    )

    try:
        create_section(db=db, section=section)

        return RedirectResponse(
            url="/section/?success=Section created successfully",
            status_code=303,
        )

    except ValueError as e:

        offices = get_all_offices(db=db)["items"]

        return templates.TemplateResponse(
            request=request,
            name="section/form.html",
            context={
                "request": request,
                "page_title": "New Section",
                "section": section,
                "offices": offices,
                "error": str(e),
            },
        )

####### Section Update router for UI ##############

#------Form to edit section details and update the same in database

@router.get("/{section_id}/edit")
def edit_section(
    section_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    section = get_section_by_id(db, section_id)

    if not section:
        raise HTTPException(
            status_code=404,
            detail="Section not found."
        )

    offices = get_all_offices(db=db)["items"]

    return templates.TemplateResponse(
        request=request,
        name="section/form.html",
        context={
            "request": request,
            "page_title": "Edit Section",
            "section": section,
            "offices": offices,
            "error": None,
            "is_edit": True,
        },
    )

#_-----------Post request to update the section details in database

@router.post("/{section_id}/edit")
def update_section_ui(
    section_id: int,
    request: Request,
    office_id: int = Form(...),
    code: str = Form(...),
    name: str = Form(...),
    remarks: str = Form(""),
    db: Session = Depends(get_db),
):

    section = SectionUpdate(
        office_id=office_id,
        code=code,
        name=name,
        remarks=remarks,
    )

    try:

        updated = update_section(
            db=db,
            section_id=section_id,
            section=section,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Section not found."
            )

        return RedirectResponse(
            url="/section/?success=Section updated successfully",
            status_code=303,
        )

    except ValueError as e:

        section.id = section_id
        offices = get_all_offices(db=db)["items"]

        return templates.TemplateResponse(
            request=request,
            name="section/form.html",
            context={
                "request": request,
                "page_title": "Edit Section",
                "section": section,
                "offices": offices,
                "error": str(e),
                "is_edit": True,
            },
        )
#----------Delete section router for UI --------------------

@router.post("/{section_id}/delete")
def delete_section_ui(
    section_id: int,
    db: Session = Depends(get_db),
):
    section = delete_section(db, section_id = section_id)

    if section is None:
        raise HTTPException(
            status_code=404,
            detail="Section not found."
        )

    return RedirectResponse(
        url="/section/?success=Section deleted successfully",
        status_code=303,
    )


#-------------Table route for live search------------

@router.get("/table", response_class=HTMLResponse)
def section_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_sections(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="section/table_container.html",
        context={
            "request": request,
            "sections": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Sections Found",
            "empty_message": "No sections are available.",
            "empty_button_text": "Add section",
            "empty_button_url": "/section/new",
        },
    )
    
    

