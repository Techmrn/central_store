from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.permissions import require_permission
from app.crud.login_history import (
    create_login_history,
    get_all_login_histories,
    get_login_history_by_id,
    record_logout,
)
from app.schemas.common import PaginatedResponse
from app.schemas.login_history import (
    LoginHistoryCreate,
    LoginHistoryRead,
    LoginHistoryDetail,
)

router = APIRouter(
    prefix="/login-histories",
    tags=["Login History"],
)


@router.post(
    "/",
    response_model=LoginHistoryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record Login Entry",
)
def add_login_entry(
    data: LoginHistoryCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_login_history(db, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=PaginatedResponse[LoginHistoryDetail],
    summary="Get All Login History Records",
)
def list_login_histories(
    search: str = Query(default=""),
    user_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None),
    page: int = Query(default=1),
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("LOGIN_HISTORY_VIEW")),
):
    return get_all_login_histories(
        db=db,
        search=search,
        user_id=user_id,
        status_filter=status_filter,
        page=page,
    )


@router.get(
    "/{history_id}",
    response_model=LoginHistoryDetail,
    summary="Get Login History By ID",
)
def get_login_history(
    history_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_permission("LOGIN_HISTORY_VIEW")),
):
    item = get_login_history_by_id(db, history_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login history record not found.",
        )
    return item


@router.post(
    "/{history_id}/logout",
    response_model=LoginHistoryRead,
    summary="Record User Logout",
)
def logout_user_session(
    history_id: int,
    db: Session = Depends(get_db),
):
    try:
        return record_logout(db, history_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
