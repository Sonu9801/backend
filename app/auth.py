"""
Core authentication module.

Handles JWT creation/validation, cookie management, session-aware
user resolution, and role-based access control.

Token flow:
  1. Login → creates session + access_token + refresh_token
  2. Access token is short-lived (15 min), delivered via HttpOnly cookie + JSON
  3. Refresh token is long-lived (30 days), delivered via HttpOnly cookie + JSON
  4. get_current_user checks cookie first, then Authorization header
  5. Session store validates that the session hasn't been revoked
  6. User cache avoids DB hit on every request
"""
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import TokenData
from app.session_store import session_store
from app.cache import user_cache

# OAuth2 scheme — still supports Bearer header for backward compatibility (PWA, mobile)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)


# ─── JWT Token Creation ─────────────────────────────────────────────────────

def create_access_token(
    data: dict,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived access token with session binding."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({
        "exp": expire,
        "type": "access",
    })
    if session_id:
        to_encode["sid"] = session_id
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: dict,
    session_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a long-lived refresh token with session binding."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({
        "exp": expire,
        "type": "refresh",
    })
    if session_id:
        to_encode["sid"] = session_id
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ─── Cookie Helpers ──────────────────────────────────────────────────────────

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    request: Optional[Request] = None,
) -> None:
    """Set HttpOnly secure cookies for both tokens. Dynamically detects HTTPS proxy tunnels."""
    is_secure = settings.COOKIE_SECURE
    if request:
        proto = request.headers.get("x-forwarded-proto", "").lower()
        referer = request.headers.get("referer", "").lower()
        origin = request.headers.get("origin", "").lower()
        if (
            request.url.scheme == "https"
            or proto == "https"
            or referer.startswith("https://")
            or origin.startswith("https://")
        ):
            is_secure = True

    cookie_kwargs = {
        "httponly": True,
        "secure": is_secure,
        "samesite": settings.COOKIE_SAMESITE,
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **cookie_kwargs,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies on logout."""
    cookie_kwargs = {"path": "/", "httponly": True}
    if settings.COOKIE_DOMAIN:
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(key="access_token", **cookie_kwargs)
    response.delete_cookie(key="refresh_token", **cookie_kwargs)


# ─── Token Extraction ────────────────────────────────────────────────────────

def _extract_token(request: Request, bearer_token: Optional[str]) -> Optional[str]:
    """Extract access token from cookie first, then Authorization header."""
    # 1. Cookie (preferred for browser clients)
    token = request.cookies.get("access_token")
    if token:
        return token
    # 2. Bearer header (for mobile / PWA / Swagger)
    return bearer_token


# ─── User Resolution (with session + cache) ──────────────────────────────────

async def get_current_user(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """
    Resolve the current user from JWT (cookie or header).
    
    Flow:
      1. Extract token from cookie or Authorization header
      2. Decode JWT, validate type=access
      3. If session_id in JWT, validate session is still active
      4. Check user cache before hitting DB
      5. Return User object
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = _extract_token(request, bearer_token)
    if not token:
        raise credentials_exception

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exception
        username: str = payload.get("sub")
        role: str = payload.get("role", "operator")
        session_id: Optional[str] = payload.get("sid")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception

    # Validate server-side session (if token has session_id)
    if session_id:
        session = session_store.get_session(session_id)
        if session is None:
            raise credentials_exception

    # Resolve user directly from DB to avoid SQLAlchemy session lifecycle bugs
    if token_data.username.startswith("worker:"):
        worker_id = int(token_data.username.split(":")[1])
        user = db.query(User).filter(User.id == worker_id).first()
        if user:
            # Dynamically attach role for RoleChecker
            user.role = token_data.role
    else:
        user = db.query(User).filter(User.email == token_data.username).first()

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user=Depends(get_current_user)):
    """Ensure the user is active (not deactivated or terminated)."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    if current_user.role == "worker" and current_user.employment_status != "Active":
        raise HTTPException(status_code=400, detail="Inactive worker")
    return current_user


# ─── Role-Based Access Control ────────────────────────────────────────────────

class RoleChecker:
    """Dependency that enforces role-based access on endpoints."""

    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user=Depends(get_current_active_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )
        return user
