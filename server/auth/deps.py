"""FastAPI dependencies for auth."""
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordBearer
from sqlmodel import Session, select

from server.auth.security import decode_token
from server.models.user import User
from server.storage import get_session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
http_bearer = HTTPBearer(auto_error=False)

ROLE_RANK = {"viewer": 1, "operator": 2, "admin": 3}


def get_current_user(
    token: Annotated[Optional[str], Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    if not payload or payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = session.exec(select(User).where(User.username == payload.sub)).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive or missing")
    return user


def require_role(min_role: str):
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if ROLE_RANK.get(user.role, 0) < ROLE_RANK.get(min_role, 99):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return checker


# Convenience
RequireViewer = Annotated[User, Depends(require_role("viewer"))]
RequireOperator = Annotated[User, Depends(require_role("operator"))]
RequireAdmin = Annotated[User, Depends(require_role("admin"))]
