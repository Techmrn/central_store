from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.crud.login_history import create_login_history
from app.crud.user import get_user_by_username
from app.core.security import (
    create_access_token,
    verify_password,
)
from app.schemas.login_history import LoginHistoryCreate


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
):
    """
    Authenticate a user and create an access token.
    """

    user = get_user_by_username(
        db=db,
        username=username,
    )

    if user is None:
        raise ValueError("Invalid username or password.")

    if not verify_password(
        password,
        user.password_hash,
    ):
        raise ValueError("Invalid username or password.")

    login_time = datetime.now(timezone.utc)

    login_history = create_login_history(
        db=db,
        login_history=LoginHistoryCreate(
            user_id=user.id,
            login_time=login_time,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        ),
    )

    access_token = create_access_token(
        data={
            "sub": str(user.id),
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
        "login_history_id": login_history.id,
    }