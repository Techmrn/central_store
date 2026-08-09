"""
Authentication Router

This module handles API endpoints related to user authentication, including:
1. User Login - Validating credentials, generating JWT access tokens, and logging login history.
2. Current User Profile (/me) - Retrieving profile details for the authenticated caller.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, LogoutRequest
from app.schemas.user import UserRead
from app.services.auth_service import authenticate_user
from app.crud.login_history import (
    get_login_history_for_user,
    record_logout,
)


# Initialize FastAPI router for authentication routes
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
)
def login(
    data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Process Flow for User Login:
    1. Extract client request metadata (IP address and User-Agent header) for audit logging.
    2. Delegate authentication logic to `authenticate_user` service:
       - Validates credentials against the database.
       - Records login history (timestamp, IP, status).
       - Generates a JWT access token.
    3. Handle errors: Convert any ValueError raised by service layer into HTTP 401 Unauthorized response.
    4. Return access token and user information.
    """
    # Step 1: Extract client IP address from request metadata
    ip_address = (
        request.client.host
        if request.client
        else None
    )

    # Step 2: Extract User-Agent header from HTTP request
    user_agent = request.headers.get(
        "user-agent"
    )

    try:
        # Step 3: Authenticate credentials, log history, and issue JWT access token
        return authenticate_user(
            db=db,
            username=data.username,
            password=data.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    except ValueError as e:
        # Step 4: Handle authentication failures (e.g. invalid username/password)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """
    Process Flow for Getting Current User Profile:
    1. `get_current_user` dependency intercepts request:
       - Extracts JWT Bearer token from Authorization header.
       - Decodes and verifies token signature and expiration.
       - Fetches matching User entity from database.
    2. Pass authenticated User object to handler function.
    3. Return user profile formatted according to UserRead schema.
    """
    # Return details of the currently authenticated user
    return current_user


#Logout request for proper history updation------

@router.post(
    "/logout",
    summary="User Logout",
)
def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    history = get_login_history_for_user(
        db=db,
        history_id=data.login_history_id,
        user_id=current_user.id,
    )

    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Login session not found.",
        )

    if history.logout_time is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Login session has already been closed.",
        )

    record_logout(
        db=db,
        history_id=history.id,
    )

    return {
        "message": "Logout recorded successfully."
    }

