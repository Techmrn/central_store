from datetime import datetime, timezone
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.login_history import LoginHistory
from app.models.user import User
from app.schemas.login_history import LoginHistoryCreate
from app.core.pagination import get_pagination_result


def create_login_history(
    db: Session,
    login_history: LoginHistoryCreate,
):
    user = db.query(User).filter(User.id == login_history.user_id, User.is_active == True).first()
    if not user:
        raise ValueError("User not found.")

    db_obj = LoginHistory(
        user_id=login_history.user_id,
        login_time=login_history.login_time or datetime.now(timezone.utc),
        logout_time=login_history.logout_time,
        ip_address=login_history.ip_address,
        user_agent=login_history.user_agent,
        status=login_history.status or "SUCCESS",
    )

    # Update last login time on User
    user.last_login = db_obj.login_time

    db.add(db_obj)
    try:
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception:
        db.rollback()
        raise


def get_all_login_histories(
    db: Session,
    search: str = "",
    user_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
):
    query = (
        db.query(LoginHistory)
        .join(User, LoginHistory.user_id == User.id)
        .options(joinedload(LoginHistory.user))
    )

    if user_id:
        query = query.filter(LoginHistory.user_id == user_id)

    if status_filter:
        query = query.filter(LoginHistory.status == status_filter)

    if search:
        search = search.strip()
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%"),
                User.code.ilike(f"%{search}%"),
                LoginHistory.ip_address.ilike(f"%{search}%"),
                LoginHistory.status.ilike(f"%{search}%"),
            )
        )

    query = query.order_by(LoginHistory.login_time.desc())

    return get_pagination_result(query=query, page=page)


def get_login_history_by_id(db: Session, history_id: int):
    return (
        db.query(LoginHistory)
        .options(joinedload(LoginHistory.user))
        .filter(LoginHistory.id == history_id)
        .first()
    )


def record_logout(db: Session, history_id: int):
    history = get_login_history_by_id(db, history_id)
    if not history:
        raise ValueError("Login history record not found.")

    history.logout_time = datetime.now(timezone.utc)

    try:
        db.commit()
        db.refresh(history)
        return history
    except Exception:
        db.rollback()
        raise
