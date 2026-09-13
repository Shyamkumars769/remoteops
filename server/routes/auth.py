from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlmodel import Session, select

from server.auth.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from server.auth.deps import RequireAdmin, get_current_user
from server.logging import auth_logger
from server.models.user import User
from server.storage import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "operator"


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form.username)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        auth_logger.warning("Failed login for %s", form.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User disabled")
    auth_logger.info("Login success user=%s role=%s", user.username, user.role)
    return TokenResponse(
        access_token=create_access_token(user.username, user.role),
        refresh_token=create_refresh_token(user.username, user.role),
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_token: str, session: Session = Depends(get_session)):
    payload = decode_token(refresh_token)
    if not payload or payload.type != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user = session.exec(select(User).where(User.username == payload.sub)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User missing")
    return TokenResponse(
        access_token=create_access_token(user.username, user.role),
        refresh_token=create_refresh_token(user.username, user.role),
        role=user.role,
    )


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"username": user.username, "role": user.role, "is_active": user.is_active}


@router.post("/users")
def create_user(body: UserCreate, admin: RequireAdmin, session: Session = Depends(get_session)):
    if body.role not in {"admin", "operator", "viewer"}:
        raise HTTPException(status_code=400, detail="Invalid role")
    existing = session.exec(select(User).where(User.username == body.username)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username taken")
    user = User(username=body.username, hashed_password=hash_password(body.password), role=body.role)
    session.add(user)
    session.commit()
    auth_logger.info("User created username=%s role=%s by=%s", body.username, body.role, admin.username)
    return {"ok": True, "username": body.username, "role": body.role}
