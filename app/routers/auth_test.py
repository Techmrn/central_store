from fastapi import APIRouter, Depends

from app.dependencies.auth import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/auth-test",
    tags=["Authentication Test"],
)


@router.get("/me")
def auth_test_me(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
    }