from fastapi import APIRouter, Depends, status
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.activity import ActivityEvent
from app.schemas.activity import ActivityEventCreate, ActivityEventResponse
from app.services.websocket_manager import manager

router = APIRouter(prefix="/activities", tags=["activities"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=List[ActivityEventResponse])
def get_activities(db: Session = Depends(get_db)):
    return db.query(ActivityEvent).order_by(ActivityEvent.timestamp.desc()).all()

@router.post("", response_model=ActivityEventResponse, status_code=status.HTTP_201_CREATED)
async def create_activity_event(event_in: ActivityEventCreate, db: Session = Depends(get_db)):
    event = ActivityEvent(**event_in.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    
    # Broadcast change
    response_data = ActivityEventResponse.model_validate(event).model_dump()
    await manager.broadcast({
        "type": "ACTIVITY_EVENT_CREATED",
        "data": response_data
    })
    return event
