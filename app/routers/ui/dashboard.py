from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.core.templates import templates
from app.dependencies.ui_auth import get_current_user_ui
from app.models.user import User

router = APIRouter(tags=["Dashboard UI"])


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_ui),
):
    return templates.TemplateResponse(
        request=request,
        name="dashboard/home.html",
        context={
            "request": request,
            "page_title": "Dashboard",
            "current_user": current_user,
        },
    )


@router.get("/", response_class=HTMLResponse)
def root_redirect():
    return RedirectResponse(
        url="/dashboard",
        status_code=status.HTTP_303_SEE_OTHER,
    )