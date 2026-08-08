from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.templates import templates
from app.crud.login_history import get_all_login_histories
from app.crud.user import get_all_users

router = APIRouter(
    prefix="/login-history",
    tags=["Login History UI"],
)


@router.get("/", response_class=HTMLResponse)
def list_login_histories_ui(
    request: Request,
    search: str = Query(default=""),
    page: int = Query(default=1),
    user_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    success: str | None = Query(None),
    error: str | None = Query(None),
    db: Session = Depends(get_db),
):
    result = get_all_login_histories(
        db=db,
        search=search,
        user_id=user_id,
        status_filter=status_filter,
        page=page,
    )

    users = get_all_users(db=db, page=1)["items"]

    return templates.TemplateResponse(
        request=request,
        name="login_history/list.html",
        context={
            "request": request,
            "page_title": "Login History Master",
            "page_subtitle": "Audit user login and session activity",
            "login_histories": result["items"],
            "pagination": result,
            "search": search,
            "users": users,
            "selected_user_id": user_id,
            "selected_status": status_filter,
            "success": success,
            "error": error,
            "empty_title": "No Login History Records",
            "empty_message": "No login activity has been recorded yet.",
        },
    )


@router.get("/table", response_class=HTMLResponse)
def login_history_table(
    request: Request,
    search: str = "",
    page: int = 1,
    user_id: int | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    result = get_all_login_histories(
        db=db,
        search=search,
        user_id=user_id,
        status_filter=status_filter,
        page=page,
    )

    return templates.TemplateResponse(
        request=request,
        name="login_history/table_container.html",
        context={
            "request": request,
            "login_histories": result["items"],
            "pagination": result,
            "search": search,
            "empty_title": "No Login History Records",
            "empty_message": "No login activity has been recorded yet.",
        },
    )
