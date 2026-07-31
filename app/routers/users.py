from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.auth import get_current_active_user
from app.config import settings
from typing import List, Optional

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(get_current_active_user)])

@router.get("")
def get_users(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from sqlalchemy import or_
    # Returns only managers/supervisors/admins, exclude workers
    query = db.query(User).filter(User.role != "worker")
    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.role.ilike(f"%{search}%"),
            )
        )
    total = query.count()
    total_pages = max(1, -(-total // page_size))
    offset = (page - 1) * page_size
    items = query.order_by(User.id).offset(offset).limit(page_size).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def invite_user(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    user = User(
        email=user_in.email,
        name=user_in.name,
        role=user_in.role or "operator",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        print("\n" + "="*50)
        print(f" NEW USER INVITED")
        print(f" Email: {user_in.email}, Role: {user_in.role}")
        print("="*50 + "\n")
        
        if settings.SMTP_USER:
            from app.email_utils import send_invite_email
            send_invite_email(user_in.email, user_in.name, user_in.role or "operator")
    except Exception as e:
        print(f"Failed to send invite email: {e}")
        pass

    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    db.delete(db_user)
    db.commit()
