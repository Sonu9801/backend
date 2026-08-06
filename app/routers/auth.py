"""
Authentication router.

Endpoints:
  POST /auth/login          — Password-based login (email/mobile + password)
  POST /auth/register       — Register a new user (with hashed password)
  POST /auth/worker-login   — Worker login (mobile + password)
  POST /auth/refresh        — Refresh access token (cookie or body)
  POST /auth/logout         — Invalidate session + clear cookies
  POST /auth/logout-all     — Invalidate ALL sessions for current user
  POST /auth/change-password — Change password (authenticated)
  GET  /auth/google         — Redirect to Google OAuth consent
  GET  /auth/google/callback — Handle Google OAuth callback
  POST /auth/device         — Register push notification device
  GET  /auth/me             — Get current user profile
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.device import Device
from app.schemas.user import UserCreate, UserResponse, LoginRequest, ChangePasswordRequest
from app.auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_current_active_user,
    set_auth_cookies,
    clear_auth_cookies,
    RoleChecker,
)
from app.security import hash_password, verify_password, needs_rehash
from app.session_store import session_store
from app.cache import user_cache
from app.config import settings
from jose import JWTError, jwt

router = APIRouter(prefix="/auth", tags=["auth"])


# ─── Request/Response Models ─────────────────────────────────────────────────

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None  # Optional — can come from cookie

class DeviceRegistrationRequest(BaseModel):
    device_token: str
    device_type: Optional[str] = None


# ─── Helper: Build login response ────────────────────────────────────────────

def _build_login_response(user: User, response: Response, request: Optional[Request] = None, is_worker: bool = False):
    """
    Shared logic for login and worker-login:
      1. Create server-side session
      2. Create JWT tokens (bound to session)
      3. Set HttpOnly cookies
      4. Update last_login
      5. Return JSON body
    """
    sub = f"worker:{user.id}" if is_worker else user.email
    role = "worker" if is_worker else user.role

    # Create session
    session_id = session_store.create_session(
        user_id=user.id,
        role=role,
        ttl_days=settings.SESSION_EXPIRE_DAYS,
    )

    # Create tokens bound to session
    token_data = {"sub": sub, "role": role}
    access_token = create_access_token(data=token_data, session_id=session_id)
    refresh_token = create_refresh_token(data=token_data, session_id=session_id)

    # Set cookies
    set_auth_cookies(response, access_token, refresh_token, request=request)

    # Update last_login (fire-and-forget, don't block on this)
    # We'll handle the DB update in the endpoint itself

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "session_id": session_id,
        "username": user.email,
        "email": user.email,
        "role": role,
        "id": user.id,
        "worker_id": user.id,
        "name": user.name,
        "employee_id": user.employee_id,
        "shift_name": user.shift_type,
        "mobile_number": user.mobile_number,
        "address": user.address,
        "emergency_contact_number": user.emergency_contact_number,
        "profile_photo_url": user.profile_photo_url,
        "designation": user.designation,
        "department": user.department,
        "aadhar_number": user.aadhaar_number,
    }


from app.models.user_login_history import UserLoginHistory

def record_login(user_id: int, request: Request, db: Session):
    try:
        user_agent = request.headers.get("user-agent", "")
        device = "Web Browser"
        if "Windows" in user_agent:
            if "Chrome" in user_agent:
                device = "Chrome on Windows"
            elif "Firefox" in user_agent:
                device = "Firefox on Windows"
            else:
                device = "Windows Device"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            if "Safari" in user_agent and "Chrome" not in user_agent:
                device = "Safari on iPhone"
            else:
                device = "iOS Device"
        elif "Android" in user_agent:
            device = "Android Device"
        elif "Macintosh" in user_agent:
            if "Safari" in user_agent and "Chrome" not in user_agent:
                device = "Safari on Mac"
            else:
                device = "Chrome on Mac"

        ip = request.client.host if request.client else "127.0.0.1"
        location = "Mumbai, India"

        history = UserLoginHistory(
            user_id=user_id,
            device=device,
            ip_address=ip,
            location=location,
            login_time=datetime.utcnow()
        )
        db.add(history)
        db.commit()
    except Exception as e:
        print(f"Failed to record login history: {e}")

# ─── POST /auth/login ────────────────────────────────────────────────────────

@router.post("/login")
def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Password-based login. Accepts email or mobile number as username.
    
    Sets HttpOnly cookies AND returns tokens in JSON body for
    backward compatibility with PWA/mobile clients.
    """
    # Try email first, then mobile number
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        user = db.query(User).filter(User.mobile_number == form_data.username).first()

    if not user or not user.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Auto-upgrade plaintext passwords to bcrypt on successful login
    if needs_rehash(user.password):
        user.password = hash_password(form_data.password)

    user.last_login = datetime.utcnow()
    db.commit()

    record_login(user.id, request, db)

    return _build_login_response(user, response, request=request)


# ─── GET /auth/setup-status ──────────────────────────────────────────────────

@router.get("/setup-status")
def setup_status(db: Session = Depends(get_db)):
    """Check if the system has no users registered yet (first-run setup)."""
    user_count = db.query(User).count()
    return {"setup_required": user_count == 0}


# ─── POST /auth/register ─────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user:
    - If 0 users in database, allow setup and force role to "admin".
    - If >0 users in database, only allow registration if user exists with password IS NULL (invite).
    """
    if not user_in.password or not user_in.password.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is required for registration",
        )
    user_count = db.query(User).count()
    
    if user_count == 0:
        # First-run setup: allow registration and force role as admin
        db_user = db.query(User).filter(User.email == user_in.email).first()
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user = User(
            email=user_in.email,
            name=user_in.name,
            role="admin",  # Force first user to be admin
            dealer_name=user_in.dealer_name,
            password=hash_password(user_in.password),
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    else:
        # Normal invite-only registration
        db_user = db.query(User).filter(User.email == user_in.email).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration is closed. Please ask your administrator for an invite.",
            )
        
        if db_user.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email has already set up a password and registered.",
            )
        
        # User is invited, but password is not set
        db_user.name = user_in.name
        db_user.password = hash_password(user_in.password)
        db_user.is_active = True
        if user_in.dealer_name:
            db_user.dealer_name = user_in.dealer_name
        
        db.commit()
        db.refresh(db_user)
        return db_user


# ─── POST /auth/worker-login ─────────────────────────────────────────────────

@router.post("/worker-login")
def worker_login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Worker login via mobile number + password/PIN."""
    worker = db.query(User).filter(
        User.mobile_number == form_data.username,
        User.employee_id.isnot(None),
    ).first()

    if not worker or not worker.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, worker.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if worker.employment_status != "Active":
        raise HTTPException(status_code=400, detail="Inactive worker")

    # Auto-upgrade plaintext passwords
    if needs_rehash(worker.password):
        worker.password = hash_password(form_data.password)

    worker.last_login = datetime.utcnow()
    db.commit()

    record_login(worker.id, request, db)

    return _build_login_response(worker, response, request=request, is_worker=True)


# ─── POST /auth/refresh ──────────────────────────────────────────────────────

@router.post("/refresh")
def refresh_access_token(
    request: Request,
    response: Response,
    body: RefreshTokenRequest = None,
    db: Session = Depends(get_db),
):
    """
    Refresh the access token.
    
    Reads refresh_token from cookie first, then from request body.
    Validates the session is still active before issuing a new access token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try cookie first, then request body
    cookie_token = request.cookies.get("refresh_token")
    body_token = body.refresh_token if body else None
    payload = None

    # 1. Try decoding refresh token from cookie
    if cookie_token:
        try:
            decoded = jwt.decode(cookie_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if decoded.get("type") == "refresh":
                payload = decoded
        except JWTError:
            pass

    # 2. Try decoding refresh token from body if cookie failed or is missing
    if not payload and body_token:
        try:
            decoded = jwt.decode(body_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if decoded.get("type") == "refresh":
                payload = decoded
        except JWTError:
            pass

    if not payload:
        raise credentials_exception

    username: str = payload.get("sub")
    role: str = payload.get("role", "operator")
    session_id: str = payload.get("sid")
    if username is None:
        raise credentials_exception

    # Validate session (if present in token)
    if session_id:
        session = session_store.get_session(session_id)
        if session is None:
            raise credentials_exception

    # Check if user still exists and is active
    if username.startswith("worker:"):
        worker_id = int(username.split(":")[1])
        user = db.query(User).filter(
            User.id == worker_id,
            User.employee_id.isnot(None),
        ).first()
        if not user or user.employment_status != "Active":
            raise credentials_exception
    else:
        user = db.query(User).filter(User.email == username).first()
        if not user or not user.is_active:
            raise credentials_exception

    # Issue new access token (same session)
    new_access_token = create_access_token(
        data={"sub": username, "role": role},
        session_id=session_id,
    )

    # Update the access_token cookie
    is_secure = settings.COOKIE_SECURE
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
        value=new_access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_kwargs,
    )

    return {"access_token": new_access_token, "token_type": "bearer"}


# ─── POST /auth/logout ───────────────────────────────────────────────────────

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user=Depends(get_current_active_user),
):
    """Invalidate the current session and clear auth cookies."""
    # Try to get session_id from the access token
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            session_id = payload.get("sid")
            if session_id:
                session_store.invalidate_session(session_id)
        except JWTError:
            pass  # Token invalid — just clear cookies anyway

    # Invalidate cache for this user
    user_cache.invalidate(f"email:{current_user.email}")
    user_cache.invalidate(f"user:{current_user.id}")

    # Clear cookies
    clear_auth_cookies(response)

    return {"message": "Logged out successfully"}


# ─── POST /auth/logout-all ───────────────────────────────────────────────────

@router.post("/logout-all")
def logout_all(
    response: Response,
    current_user=Depends(get_current_active_user),
):
    """Invalidate ALL sessions for the current user (logout everywhere)."""
    count = session_store.invalidate_all_user_sessions(current_user.id)

    # Invalidate cache
    user_cache.invalidate(f"email:{current_user.email}")
    user_cache.invalidate(f"user:{current_user.id}")

    # Clear cookies on this device
    clear_auth_cookies(response)

    return {"message": f"Logged out from {count} session(s)"}


# ─── POST /auth/change-password ──────────────────────────────────────────────

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Change password for the authenticated user."""
    if not current_user.password:
        raise HTTPException(
            status_code=400,
            detail="Account uses OAuth login. Set a password first.",
        )

    if not verify_password(payload.old_password, current_user.password):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect",
        )

    current_user.password = hash_password(payload.new_password)
    db.commit()

    # Invalidate cache so next request picks up updated user
    user_cache.invalidate(f"email:{current_user.email}")
    user_cache.invalidate(f"user:{current_user.id}")

    return {"message": "Password changed successfully"}




# ─── POST /auth/device ────────────────────────────────────────────────────────

@router.post("/device", status_code=status.HTTP_201_CREATED)
def register_device(
    request_body: DeviceRegistrationRequest,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Register a push notification device token."""
    device = db.query(Device).filter(
        Device.device_token == request_body.device_token
    ).first()

    if device:
        device.user_id = current_user.id
        device.device_type = request_body.device_type
        device.is_active = True
    else:
        device = Device(
            device_token=request_body.device_token,
            device_type=request_body.device_type,
            user_id=current_user.id,
        )
        db.add(device)
    db.commit()
    return {"message": "Device registered successfully"}


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Get the current authenticated user's profile."""
    return current_user


@router.get("/login-history")
def get_login_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve recent login activity for the authenticated user."""
    history = db.query(UserLoginHistory).filter(
        UserLoginHistory.user_id == current_user.id
    ).order_by(UserLoginHistory.login_time.desc()).limit(10).all()
    
    return [
        {
            "device": h.device,
            "ip": h.ip_address,
            "location": h.location,
            "time": h.login_time.isoformat() + "Z"
        }
        for h in history
    ]
