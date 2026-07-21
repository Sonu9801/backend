from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.auth import create_access_token, create_refresh_token, get_current_user, get_current_active_user, RoleChecker
from jose import JWTError, jwt
from app.config import settings
from pydantic import BaseModel
from typing import Optional
import smtplib
import random
from email.message import EmailMessage
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

class OtpRequest(BaseModel):
    email: str

class OtpVerify(BaseModel):
    email: str
    otp_code: str

@router.post("/request-otp")
def request_otp(data: OtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not registered"
        )
        
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.commit()

    try:
        # Always print OTP for local development visibility
        print("\n" + "="*50)
        print(f" NEW OTP REQUESTED")
        print(f" OTP for {user.email} is: {otp}")
        print("="*50 + "\n")
        
        if settings.SMTP_USER:
            from app.email_utils import send_otp_email
            send_otp_email(data.email, otp, user.name)
            
    except Exception as e:
        print(f"Failed to send email: {e}")
        # Return success anyway for dev mode so they can still see it in console
        pass

    return {"message": "OTP sent successfully"}

@router.post("/verify-otp")
def verify_otp(data: OtpVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or OTP",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if user.otp_code != data.otp_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or OTP",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.otp_expires_at or user.otp_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP has expired",
        )

    if hasattr(user, "is_active") and not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    user.otp_code = None
    user.otp_expires_at = None
    db.commit()

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": user.role})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user.email,
        "role": user.role,
        "name": user.name
    }

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class DeviceRegistrationRequest(BaseModel):
    device_token: str
    device_type: Optional[str] = None

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    # hashed_pwd = get_password_hash(user_in.password) # UserCreate has no password
    user = User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role,
        dealer_name=user_in.dealer_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try email first, then mobile number
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        user = db.query(User).filter(User.mobile_number == form_data.username).first()
        
    if not user or user.password != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email/mobile or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    refresh_token = create_refresh_token(data={"sub": user.email, "role": user.role})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "username": user.email,
        "role": user.role,
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

@router.post("/worker-login")
def worker_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Assuming username field is used for mobile number
    worker = db.query(User).filter(User.mobile_number == form_data.username, User.role.ilike("worker")).first()
    if not worker or worker.password != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if worker.employment_status != "Active":
        raise HTTPException(status_code=400, detail="Inactive worker")
    
    # We prefix worker token sub with 'worker:' to distinguish from admin users if needed
    sub = f"worker:{worker.id}"
    access_token = create_access_token(data={"sub": sub, "role": "worker"})
    refresh_token = create_refresh_token(data={"sub": sub, "role": "worker"})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "worker_id": worker.id,
        "id": worker.id,
        "name": worker.name,
        "role": "worker",
        "employee_id": worker.employee_id,
        "shift_name": worker.shift_type,
        "mobile_number": worker.mobile_number,
        "address": worker.address,
        "emergency_contact_number": worker.emergency_contact_number,
        "profile_photo_url": worker.profile_photo_url,
        "designation": worker.designation,
        "department": worker.department,
        "aadhar_number": worker.aadhaar_number,
    }

@router.post("/refresh")
def refresh_access_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(body.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        username: str = payload.get("sub")
        role: str = payload.get("role", "operator")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Check if user still exists/active
    if username.startswith("worker:"):
        worker_id = int(username.split(":")[1])
        user = db.query(User).filter(User.id == worker_id, User.role.ilike("worker")).first()
        if not user or user.employment_status != "Active":
            raise credentials_exception
    else:
        user = db.query(User).filter(User.email == username).first()
        if not user or not user.is_active:
            raise credentials_exception

    new_access_token = create_access_token(data={"sub": username, "role": role})
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/device", status_code=status.HTTP_201_CREATED)
def register_device(
    request: DeviceRegistrationRequest, 
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    device = db.query(Device).filter(Device.device_token == request.device_token).first()
    
    if hasattr(current_user, "employment_status"):
        worker_id = current_user.id
        user_id = None
    else:
        user_id = current_user.id
        worker_id = None
        
    if device:
        device.user_id = user_id
        device.worker_id = worker_id
        device.device_type = request.device_type
        device.is_active = True
    else:
        device = Device(
            device_token=request.device_token,
            device_type=request.device_type,
            user_id=user_id,
            worker_id=worker_id
        )
        db.add(device)
    db.commit()
    return {"message": "Device registered successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

