from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.role import (
    get_all_roles,
    get_role_by_id,
    create_role,
    update_role,
    delete_role,
)
from app.schemas.role import RoleCreate, RoleUpdate

router = APIRouter(
    prefix="/role",
    tags=["Role UI"],
)


# ---------------------------------------------------------
# Role List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_roles(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_roles(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="role/list.html",
        context={
            "request": request,
            "page_title": "Role Master",
            "page_subtitle": "Manage roles for user access control",
            "roles": result["items"],
            "pagination": result,
            "search": search,
            "new_button_url": "/role/new",
            "new_button_text": "New Role",
            "success": success,
            "error": error,
            "empty_title": "No Roles Found",
            "empty_message": "No roles are available.",
            "empty_button_text": "Add Role",
            "empty_button_url": "/role/new",
        },
    )


# ---------------------------------------------------------
# Role Create
# ---------------------------------------------------------

@router.get("/new")
def new_role(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="role/form.html",
        context={
            "request": request,
            "page_title": "New Role",
            "error": None,
            "is_edit": False,
        },
    )


@router.post("/new")
def create_role_ui(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):
    role = RoleCreate(
        code=code,
        name=name,
        description=description,
    )

    try:
        create_role(db=db, role=role)

        return RedirectResponse(
            url="/role/?success=Role created successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="role/form.html",
            context={
                "request": request,
                "page_title": "New Role",
                "error": str(e),
                "role": role,
            },
        )


# ---------------------------------------------------------
# Role Update
# ---------------------------------------------------------

@router.get("/{role_id}/edit")
def edit_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    role = get_role_by_id(db, role_id)

    if not role:
        raise HTTPException(
            status_code=404,
            detail="Role not found."
        )

    return templates.TemplateResponse(
        request=request,
        name="role/form.html",
        context={
            "request": request,
            "page_title": "Edit Role",
            "role": role,
            "role_id": role.id,
            "error": None,
            "is_edit": True,
        },
    )


@router.post("/{role_id}/edit")
def update_role_ui(
    role_id: int,
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):

    role = RoleUpdate(
        code=code,
        name=name,
        description=description,
    )

    try:

        updated = update_role(
            db=db,
            role_id=role_id,
            role=role,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Role not found."
            )

        return RedirectResponse(
            url="/role/?success=Role updated successfully",
            status_code=303,
        )

    except ValueError as e:

        return templates.TemplateResponse(
            request=request,
            name="role/form.html",
            context={
                "request": request,
                "page_title": "Edit Role",
                "role": role,
                "role_id": role_id,
                "error": str(e),
                "is_edit": True,
            },
        )


# ---------------------------------------------------------
# Role Delete
# ---------------------------------------------------------

@router.post("/{role_id}/delete")
def delete_role_ui(
    role_id: int,
    db: Session = Depends(get_db),
):
    try:
        role = delete_role(db, role_id=role_id)

        if role is None:
            raise HTTPException(
                status_code=404,
                detail="Role not found."
            )

        return RedirectResponse(
            url="/role/?success=Role deleted successfully",
            status_code=303,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


# ---------------------------------------------------------
# Table route for live search
# ---------------------------------------------------------

@router.get("/table", response_class=HTMLResponse)
def role_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_roles(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="role/table_container.html",
        context={
            "request": request,
            "roles": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Roles Found",
            "empty_message": "No roles are available.",
            "empty_button_text": "Add Role",
            "empty_button_url": "/role/new",
        },
    )