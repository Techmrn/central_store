from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.permission import (
    create_permission,
    delete_permission,
    get_all_permissions,
    get_permission_by_id,
    update_permission,
)
from app.schemas.permission import PermissionCreate, PermissionUpdate

router = APIRouter(
    prefix="/permission",
    tags=["Permission UI"],
)


# ---------------------------------------------------------
# Permission List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_permissions(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = get_all_permissions(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="permission/list.html",
        context={
            "request": request,
            "page_title": "Permission Master",
            "page_subtitle": "Manage permissions for granular access control",
            "permissions": result["items"],
            "pagination": result,
            "search": search,
            "new_button_url": "/permission/new",
            "new_button_text": "New Permission",
            "success": success,
            "error": error,
            "empty_title": "No Permissions Found",
            "empty_message": "No permissions are available.",
            "empty_button_text": "Add Permission",
            "empty_button_url": "/permission/new",
        },
    )


# ---------------------------------------------------------
# Permission Create
# ---------------------------------------------------------

@router.get("/new", response_class=HTMLResponse)
def new_permission(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="permission/form.html",
        context={
            "request": request,
            "page_title": "New Permission",
            "error": None,
            "is_edit": False,
        },
    )


@router.post("/new")
def create_permission_ui(
    request: Request,
    module: str = Form(...),
    action: str = Form(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):
    permission = PermissionCreate(
        module=module,
        action=action,
        description=description,
    )

    try:
        create_permission(db=db, permission=permission)
        return RedirectResponse(
            url="/permission/?success=Permission created successfully",
            status_code=303,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="permission/form.html",
            context={
                "request": request,
                "page_title": "New Permission",
                "error": str(e),
                "permission": permission,
                "is_edit": False,
            },
        )


# ---------------------------------------------------------
# Permission Update
# ---------------------------------------------------------

@router.get("/{permission_id}/edit", response_class=HTMLResponse)
def edit_permission(
    permission_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    permission = get_permission_by_id(db, permission_id)

    if not permission:
        raise HTTPException(
            status_code=404,
            detail="Permission not found.",
        )

    return templates.TemplateResponse(
        request=request,
        name="permission/form.html",
        context={
            "request": request,
            "page_title": "Edit Permission",
            "permission": permission,
            "permission_id": permission.id,
            "error": None,
            "is_edit": True,
        },
    )


@router.post("/{permission_id}/edit")
def update_permission_ui(
    permission_id: int,
    request: Request,
    module: str = Form(...),
    action: str = Form(...),
    description: str = Form(default=None),
    db: Session = Depends(get_db),
):
    permission = PermissionUpdate(
        module=module,
        action=action,
        description=description,
    )

    try:
        updated = update_permission(
            db=db,
            permission_id=permission_id,
            permission=permission,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="Permission not found.",
            )

        return RedirectResponse(
            url="/permission/?success=Permission updated successfully",
            status_code=303,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            request=request,
            name="permission/form.html",
            context={
                "request": request,
                "page_title": "Edit Permission",
                "permission": permission,
                "permission_id": permission_id,
                "error": str(e),
                "is_edit": True,
            },
        )


# ---------------------------------------------------------
# Permission Delete
# ---------------------------------------------------------

@router.post("/{permission_id}/delete")
def delete_permission_ui(
    permission_id: int,
    db: Session = Depends(get_db),
):
    try:
        permission = delete_permission(db, permission_id=permission_id)

        if permission is None:
            raise HTTPException(
                status_code=404,
                detail="Permission not found.",
            )

        return RedirectResponse(
            url="/permission/?success=Permission deleted successfully",
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
def permission_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):
    result = get_all_permissions(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="permission/table_container.html",
        context={
            "request": request,
            "permissions": result["items"],
            "pagination": result,
            "search": search,
            "empty_title": "No Permissions Found",
            "empty_message": "No permissions are available.",
            "empty_button_text": "Add Permission",
            "empty_button_url": "/permission/new",
        },
    )
