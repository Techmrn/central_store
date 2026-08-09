from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import decode_access_token
from app.models.user import User


def get_current_user_ui(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate a UI request using the JWT stored in an HttpOnly cookie.
    If unauthenticated or token is invalid, redirects the browser to /login.
    """
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    try:
        payload = decode_access_token(token)
        user_id_raw = payload.get("sub")
        if not user_id_raw:
            raise ValueError("Token missing sub claim")
        user_id = int(user_id_raw)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_active.is_(True),
        )
        .first()
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    return user
