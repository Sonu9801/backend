from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    role: Optional[str] = "operator"
    dealer_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str

    class Config:
        from_attributes = True

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    email: str
    name: str
    role: str

class TokenData(BaseModel):
    username: Optional[str] = None  # kept as "username" internally for JWT sub compatibility
    role: Optional[str] = None
