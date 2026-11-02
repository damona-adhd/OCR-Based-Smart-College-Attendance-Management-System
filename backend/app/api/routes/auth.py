from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import verify_password, create_access_token, create_refresh_token, decode_token
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import TokenResponse, RefreshRequest, UserOut, LoginRequest
from app.services.audit_service import log_event
from jose import JWTError

router = APIRouter(prefix="/auth", tags=["Authentication"])

ROLE_ALIASES = {
    "admin": UserRole.ADMIN,
    "teacher": UserRole.LECTURER,
    "lecturer": UserRole.LECTURER,
    "student": UserRole.STUDENT,
}


def _map_expected_role(raw: str | None) -> UserRole | None:
    if not raw:
        return None
    mapped = ROLE_ALIASES.get(raw.strip().lower())
    if not mapped:
        raise HTTPException(status_code=400, detail="Invalid role selection")
    return mapped


async def _authenticate(db: AsyncSession, username: str, password: str, expected: UserRole | None) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    if expected is not None and user.role != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account does not match the selected role",
        )
    return user


def _tokens(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id, extra_claims={"role": user.role}),
        refresh_token=create_refresh_token(user.id),
        role=user.role,
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    content_type = (request.headers.get("content-type") or "").lower()
    expected = None
    if "application/json" in content_type:
        payload = await request.json()
        body = LoginRequest(**payload)
        username, password = body.username, body.password
        expected = _map_expected_role(body.expected_role)
    else:
        form = await request.form()
        username = str(form.get("username") or "")
        password = str(form.get("password") or "")
        expected = _map_expected_role(str(form.get("expected_role")) if form.get("expected_role") else None)

    user = await _authenticate(db, username, password, expected)
    await log_event(db, action="user_login", actor_user_id=user.id, entity_type="user", entity_id=user.id)
    await db.commit()
    return _tokens(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    credentials_exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise credentials_exc
        user_id = payload.get("sub")
    except JWTError:
        raise credentials_exc

    user = await db.get(User, int(user_id))
    if not user or not user.is_active:
        raise credentials_exc
    return _tokens(user)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
