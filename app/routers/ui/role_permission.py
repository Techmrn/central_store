from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.role_permission import (
    get_all_role_permissions,
    get_role_permission_by_id,
    create_role_permission,
    delete_role_permission,
)
from app.crud.role import get_all_roles
from app.crud.permission import get_all_permissions
from app.schemas.role_permission import RolePermissionCreate

router = APIRouter(
    prefix="/role-permission",
    tags=["Role Permission UI"],
)


@router.get("/", response_class=HTMLResponse)
def list_role_permissions_ui(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    role_id: int | None = Query(default=None),
    permission_id: int | None = Query(default=None),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = get_all_role_permissions(
        db=db,
        search=search,
        role_id=role_id,
        permission_id=permission_id,
        page=page,
    )

    roles = get_all_roles(db=db, page=1)["items"]
    permissions = get_all_permissions(db=db, page=1)["items"]

    return templates.TemplateResponse(
        request=request,
        name="role_permission/list.html",
        context={
            "request": request,
            "page_title": "Role Permission Master",
            "page_subtitle": "Map permissions to system roles",
            "role_permissions": result["items"],
            "pagination": result,
            "search": search,
            "roles": roles,
            "permissions": permissions,
            "selected_role_id": role_id,
            "selected_permission_id": permission_id,
            "new_button_url": "/role-permission/new",
            "new_button_text": "Assign Permission",
            "success": success,
            "error": error,
            "empty_title": "No Mappings Found",
            "empty_message": "No role permissions are currently mapped.",
            "empty_button_text": "Assign Permission",
            "empty_button_url": "/role-permission/new",
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_role_permission_ui(
    request: Request,
    db: Session = Depends(get_db),
):
    roles = get_all_roles(db=db, page=1)["items"]
    permissions = get_all_permissions(db=db, page=1)["items"]

    return templates.TemplateResponse(
        request=request,
        name="role_permission/form.html",
        context={
            "request": request,
            "page_title": "Assign Permission to Role",
            "roles": roles,
            "permissions": permissions,
            "error": None,
        },
    )


@router.post("/new")
def create_role_permission_ui(
    request: Request,
    role_id: int = Form(...),
    permission_id: int = Form(...),
    db: Session = Depends(get_db),
):
    data = RolePermissionCreate(
        role_id=role_id,
        permission_id=permission_id,
    )

    try:
        create_role_permission(db=db, role_permission=data)
        return RedirectResponse(
            url="/role-permission/?success=Permission assigned to role successfully",
            status_code=303,
        )
    except ValueError as e:
        roles = get_all_roles(db=db, page=1)["items"]
        permissions = get_all_permissions(db=db, page=1)["items"]
        return templates.TemplateResponse(
            request=request,
            name="role_permission/form.html",
            context={
                "request": request,
                "page_title": "Assign Permission to Role",
                "roles": roles,
                "permissions": permissions,
                "selected_role_id": role_id,
                "selected_permission_id": permission_id,
                "error": str(e),
            },
        )


@router.post("/{role_permission_id}/delete")
def delete_role_permission_ui(
    role_permission_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_role_permission(db, role_permission_id=role_permission_id)
        return RedirectResponse(
            url="/role-permission/?success=Role permission mapping removed successfully",
            status_code=303,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.get("/table", response_class=HTMLResponse)
def role_permission_table(
    request: Request,
    search: str = "",
    page: int = 1,
    role_id: int | None = None,
    permission_id: int | None = None,
    db: Session = Depends(get_db),
):
    result = get_all_role_permissions(
        db=db,
        search=search,
        role_id=role_id,
        permission_id=permission_id,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="role_permission/table_container.html",
        context={
            "request": request,
            "role_permissions": result["items"],
            "pagination": result,
            "search": search,
            "empty_title": "No Mappings Found",
            "empty_message": "No role permissions are currently mapped.",
            "empty_button_text": "Assign Permission",
            "empty_button_url": "/role-permission/new",
        },
    )
