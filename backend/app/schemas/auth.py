from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str
    expected_role: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    username: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    is_active: bool
    full_name: Optional[str] = None

    model_config = {"from_attributes": True}
