from pydantic import BaseModel, ConfigDict

from app.schemas.user import UserRead

#authenticate current user 

class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    login_history_id: int


class AuthUserResponse(UserRead):
    model_config = ConfigDict(from_attributes=True)


class LogoutRequest(BaseModel):
    login_history_id: int