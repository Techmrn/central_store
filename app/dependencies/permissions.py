from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User
from app.dependencies.auth import get_current_user
from app.dependencies.ui_auth import get_current_user_ui
from app.services.permission_service import has_permission


def require_permission(permission_code: str):
    """
    Create a FastAPI dependency that requires a specific permission.
    """

    def permission_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:

        if not has_permission(
            db=db,
            user_id=current_user.id,
            permission_code=permission_code,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return permission_checker


def require_permission_ui(permission_code: str):
    """
    Create a FastAPI dependency that requires a specific permission for UI requests.
    """

    def permission_checker_ui(
        current_user: User = Depends(get_current_user_ui),
        db: Session = Depends(get_db),
    ) -> User:

        if not has_permission(
            db=db,
            user_id=current_user.id,
            permission_code=permission_code,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )

        return current_user

    return permission_checker_ui