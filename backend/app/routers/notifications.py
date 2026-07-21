from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.notification import Notification
from pydantic import BaseModel

router = APIRouter(tags=["notifications"], dependencies=[Depends(get_current_active_user)])

class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    message: str
    module: str
    reference_id: str | None
    target_url: str | None
    assigned_role: str | None
    assigned_user_id: int | None
    read: bool
    clicked: bool
    archived: bool
    timestamp: datetime
    
    class Config:
        orm_mode = True

@router.get("/notifications", response_model=List[NotificationOut])
def get_notifications(
    skip: int = 0, 
    limit: int = 100, 
    unread_only: bool = False,
    role: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Notification).filter(Notification.archived == False)
    
    if unread_only:
        query = query.filter(Notification.read == False)
    
    if role:
        # In a real app we would check current user's role
        # Here we filter by assigned_role if provided
        query = query.filter((Notification.assigned_role == role) | (Notification.assigned_role == None))
        
    notifications = query.order_by(Notification.timestamp.desc()).offset(skip).limit(limit).all()
    return notifications

@router.post("/notifications/{notification_id}/read")
def mark_as_read(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    return {"status": "success"}

@router.post("/notifications/{notification_id}/click")
def mark_as_clicked(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
        
    notification.clicked = True
    notification.clicked_at = datetime.utcnow()
    # Implicitly mark as read when clicked
    if not notification.read:
        notification.read = True
        notification.read_at = datetime.utcnow()
        
    db.commit()
    return {"status": "success", "target_url": notification.target_url}

@router.post("/notifications/read-all")
def mark_all_as_read(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.read == False).update(
        {"read": True, "read_at": datetime.utcnow()}
    )
    db.commit()
    return {"status": "success"}
