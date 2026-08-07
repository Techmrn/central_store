from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates

from app.models.office import Office
from app.models.section import Section

from app.crud.user import (
    get_all_users,
    get_user_by_id,
    create_user,
    update_user,
    delete_user,
)
from app.schemas.user import UserCreate, UserUpdate

router = APIRouter(
    prefix="/user",
    tags=["User UI"],
)


# ---------------------------------------------------------
# User List
# ---------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def list_users(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):

    result = get_all_users(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="user/list.html",
        context={
            "request": request,
            "page_title": "User Master",
            "page_subtitle": "Manage system users and their access",
            "users": result["items"],
            "pagination": result,
            "search": search,
            "new_button_url": "/user/new",
            "new_button_text": "New User",
            "success": success,
            "error": error,
            "empty_title": "No Users Found",
            "empty_message": "No users are available.",
            "empty_button_text": "Add User",
            "empty_button_url": "/user/new",
        },
    )


# ---------------------------------------------------------
# User Create
# ---------------------------------------------------------

@router.get("/new")
def new_user(
    request: Request,
    db: Session = Depends(get_db),
):
    offices = (
        db.query(Office)
        .filter(Office.is_active == True)
        .order_by(Office.name)
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="user/form.html",
        context={
            "request": request,
            "page_title": "New User",
            "user": None,
            "error": None,
            "is_edit": False,
            "offices": offices,
            "sections": [],
        },
    )


@router.post("/new")
def create_user_ui(
    request: Request,
    code: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    designation: str = Form(default=None),
    office_id: int = Form(...),
    section_id: int = Form(default=None),
    email: str = Form(default=None),
    mobile: str = Form(default=None),
    remarks: str = Form(default=None),
    db: Session = Depends(get_db),
):

    user = UserCreate(
        code=code,
        username=username,
        password=password,
        full_name=full_name,
        designation=designation if designation else None,
        office_id=office_id,
        section_id=section_id if section_id else None,
        email=email if email else None,
        mobile=mobile if mobile else None,
        remarks=remarks if remarks else None,
    )

    try:
        create_user(db=db, user=user)

        return RedirectResponse(
            url="/user/?success=User created successfully",
            status_code=303,
        )

    except ValueError as e:
        offices = (
            db.query(Office)
            .filter(Office.is_active == True)
            .order_by(Office.name)
            .all()
        )

        sections = []
        if office_id:
            sections = (
                db.query(Section)
                .filter(
                    Section.office_id == office_id,
                    Section.is_active == True,
                )
                .order_by(Section.name)
                .all()
            )

        return templates.TemplateResponse(
            request=request,
            name="user/form.html",
            context={
                "request": request,
                "page_title": "New User",
                "error": str(e),
                "user": user,
                "is_edit": False,
                "offices": offices,
                "sections": sections,
            },
        )


# ---------------------------------------------------------
# User Update
# ---------------------------------------------------------

@router.get("/{user_id}/edit")
def edit_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found."
        )

    offices = (
        db.query(Office)
        .filter(Office.is_active == True)
        .order_by(Office.name)
        .all()
    )

    sections = []
    if user.section_id:
        sections = (
            db.query(Section)
            .filter(
                Section.office_id == user.office_id,
                Section.is_active == True,
            )
            .order_by(Section.name)
            .all()
        )

    return templates.TemplateResponse(
        request=request,
        name="user/form.html",
        context={
            "request": request,
            "page_title": "Edit User",
            "user": user,
            "user_id": user.id,
            "error": None,
            "is_edit": True,
            "offices": offices,
            "sections": sections,
        },
    )


@router.post("/{user_id}/edit")
def update_user_ui(
    user_id: int,
    request: Request,
    code: str = Form(...),
    username: str = Form(...),
    password: str = Form(default=None),
    full_name: str = Form(...),
    designation: str = Form(default=None),
    office_id: int = Form(...),
    section_id: int = Form(default=None),
    email: str = Form(default=None),
    mobile: str = Form(default=None),
    remarks: str = Form(default=None),
    db: Session = Depends(get_db),
):

    user = UserUpdate(
        code=code,
        username=username,
        full_name=full_name,
        designation=designation if designation else None,
        office_id=office_id,
        section_id=section_id if section_id else None,
        email=email if email else None,
        mobile=mobile if mobile else None,
        remarks=remarks if remarks else None,
    )

    if password:
        user.password = password

    try:

        updated = update_user(
            db=db,
            user_id=user_id,
            user=user,
        )

        if updated is None:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        return RedirectResponse(
            url="/user/?success=User updated successfully",
            status_code=303,
        )

    except ValueError as e:

        offices = (
            db.query(Office)
            .filter(Office.is_active == True)
            .order_by(Office.name)
            .all()
        )

        sections = []
        if office_id:
            sections = (
                db.query(Section)
                .filter(
                    Section.office_id == office_id,
                    Section.is_active == True,
                )
                .order_by(Section.name)
                .all()
            )

        return templates.TemplateResponse(
            request=request,
            name="user/form.html",
            context={
                "request": request,
                "page_title": "Edit User",
                "user": user,
                "user_id": user_id,
                "error": str(e),
                "is_edit": True,
                "offices": offices,
                "sections": sections,
            },
        )


# ---------------------------------------------------------
# User Delete
# ---------------------------------------------------------

@router.post("/{user_id}/delete")
def delete_user_ui(
    user_id: int,
    db: Session = Depends(get_db),
):
    try:
        user = delete_user(db, user_id=user_id)

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="User not found."
            )

        return RedirectResponse(
            url="/user/?success=User deleted successfully",
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
def user_table(
    request: Request,
    search: str = "",
    page: int = 1,
    db: Session = Depends(get_db),
):

    result = get_all_users(
        db=db,
        search=search,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="user/table_container.html",
        context={
            "request": request,
            "users": result["items"],
            "pagination": result,
            "search": search,

            "empty_title": "No Users Found",
            "empty_message": "No users are available.",
            "empty_button_text": "Add User",
            "empty_button_url": "/user/new",
        },
    )