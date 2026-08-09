from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.core.templates import templates
from app.crud.login_history import record_logout
from app.models.login_history import LoginHistory
from app.services.auth_service import authenticate_user

router = APIRouter(tags=["UI Authentication"])


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    """
    Render the UI login page.
    """
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"request": request},
    )


@router.post("/login")
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    Process browser UI login form submission.
    """
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    try:
        auth_data = authenticate_user(
            db=db,
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        response = RedirectResponse(
            url="/dashboard",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        response.set_cookie(
            key="access_token",
            value=auth_data["access_token"],
            httponly=True,
            samesite="lax",
        )
        return response

    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "request": request,
                "error": "Invalid username or password.",
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )


@router.get("/logout")
def logout(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Process browser UI logout by clearing the HttpOnly access token cookie.
    """
    token = request.cookies.get("access_token")

    if token:
        try:
            payload = decode_access_token(token)
            user_id_raw = payload.get("sub")
            if user_id_raw:
                user_id = int(user_id_raw)
                active_session = (
                    db.query(LoginHistory)
                    .filter(
                        LoginHistory.user_id == user_id,
                        LoginHistory.logout_time.is_(None),
                    )
                    .order_by(LoginHistory.login_time.desc())
                    .first()
                )
                if active_session:
                    record_logout(db, active_session.id)
        except Exception:
            pass

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(key="access_token")
    return response
