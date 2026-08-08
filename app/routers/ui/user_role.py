from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.user_role import (
    get_all_user_roles,
    get_user_role_by_id,
    create_user_role,
    delete_user_role,
)
from app.crud.user import get_all_users
from app.crud.role import get_all_roles
from app.schemas.user_role import UserRoleCreate

router = APIRouter(
    prefix="/user-role",
    tags=["User Role UI"],
)


@router.get("/", response_class=HTMLResponse)
def list_user_roles_ui(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    user_id: int | None = Query(default=None),
    role_id: int | None = Query(default=None),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = get_all_user_roles(
        db=db,
        search=search,
        user_id=user_id,
        role_id=role_id,
        page=page,
    )

    users = get_all_users(db=db, page=1)["items"]
    roles = get_all_roles(db=db, page=1)["items"]

    return templates.TemplateResponse(
        request=request,
        name="user_role/list.html",
        context={
            "request": request,
            "page_title": "User Role Master",
            "page_subtitle": "Assign roles to users",
            "user_roles": result["items"],
            "pagination": result,
            "search": search,
            "users": users,
            "roles": roles,
            "selected_user_id": user_id,
            "selected_role_id": role_id,
            "new_button_url": "/user-role/new",
            "new_button_text": "Assign Role",
            "success": success,
            "error": error,
            "empty_title": "No User Roles Found",
            "empty_message": "No roles are assigned to users yet.",
            "empty_button_text": "Assign Role",
            "empty_button_url": "/user-role/new",
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_user_role_ui(
    request: Request,
    db: Session = Depends(get_db),
):
    users = get_all_users(db=db, page=1)["items"]
    roles = get_all_roles(db=db, page=1)["items"]

    return templates.TemplateResponse(
        request=request,
        name="user_role/form.html",
        context={
            "request": request,
            "page_title": "Assign Role to User",
            "users": users,
            "roles": roles,
            "error": None,
        },
    )


@router.post("/new")
def create_user_role_ui(
    request: Request,
    user_id: int = Form(...),
    role_id: int = Form(...),
    db: Session = Depends(get_db),
):
    data = UserRoleCreate(
        user_id=user_id,
        role_id=role_id,
    )

    try:
        create_user_role(db=db, user_role=data)
        return RedirectResponse(
            url="/user-role/?success=Role assigned to user successfully",
            status_code=303,
        )
    except ValueError as e:
        users = get_all_users(db=db, page=1)["items"]
        roles = get_all_roles(db=db, page=1)["items"]
        return templates.TemplateResponse(
            request=request,
            name="user_role/form.html",
            context={
                "request": request,
                "page_title": "Assign Role to User",
                "users": users,
                "roles": roles,
                "selected_user_id": user_id,
                "selected_role_id": role_id,
                "error": str(e),
            },
        )


@router.post("/{user_role_id}/delete")
def delete_user_role_ui(
    user_role_id: int,
    db: Session = Depends(get_db),
):
    try:
        delete_user_role(db, user_role_id=user_role_id)
        return RedirectResponse(
            url="/user-role/?success=User role mapping removed successfully",
            status_code=303,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        )


@router.get("/table", response_class=HTMLResponse)
def user_role_table(
    request: Request,
    search: str = "",
    page: int = 1,
    user_id: int | None = None,
    role_id: int | None = None,
    db: Session = Depends(get_db),
):
    result = get_all_user_roles(
        db=db,
        search=search,
        user_id=user_id,
        role_id=role_id,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="user_role/table_container.html",
        context={
            "request": request,
            "user_roles": result["items"],
            "pagination": result,
            "search": search,
            "empty_title": "No User Roles Found",
            "empty_message": "No roles are assigned to users yet.",
            "empty_button_text": "Assign Role",
            "empty_button_url": "/user-role/new",
        },
    )
