from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.dispatch import DispatchRecord
from app.schemas.dispatch import DispatchRecordCreate, DispatchRecordResponse
from app.services.websocket_manager import manager

router = APIRouter(prefix="/dispatch", tags=["dispatch"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=List[DispatchRecordResponse])
def get_dispatch_records(db: Session = Depends(get_db)):
    return db.query(DispatchRecord).order_by(DispatchRecord.scheduled_date.desc()).all()

@router.post("", response_model=DispatchRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_dispatch_record(dispatch_in: DispatchRecordCreate, db: Session = Depends(get_db)):
    dispatch_record = DispatchRecord(**dispatch_in.model_dump())
    db.add(dispatch_record)
    db.commit()
    db.refresh(dispatch_record)
    
    # Broadcast change
    response_data = DispatchRecordResponse.model_validate(dispatch_record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_RECORD_CREATED",
        "data": response_data
    })
    return dispatch_record

@router.patch("/{record_id}/status", response_model=DispatchRecordResponse)
async def update_dispatch_status(record_id: int, status: str, db: Session = Depends(get_db)):
    record = db.query(DispatchRecord).filter(DispatchRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
    record.status = status
    
    if status.lower() == "delayed":
        from app.models.notification import Notification
        notification = Notification(
            type="warning",
            title="Dispatch Delayed",
            message=f"Dispatch for vehicle {record.vehicle_id} has been delayed.",
            module="dispatch",
            reference_id=str(record.id),
            target_url="/dispatch",
        )
        db.add(notification)

    db.commit()
    db.refresh(record)
    
    # Broadcast status update
    response_data = DispatchRecordResponse.model_validate(record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_STATUS_CHANGED",
        "data": response_data
    })
    return record

from app.schemas.dispatch import DispatchRecordUpdate
from datetime import datetime

@router.put("/{record_id}", response_model=DispatchRecordResponse)
async def update_dispatch_record(record_id: int, update_in: DispatchRecordUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    record = db.query(DispatchRecord).filter(DispatchRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
        
    old_data = DispatchRecordResponse.model_validate(record).model_dump()
    update_data = update_in.model_dump(exclude_unset=True)
    reason = update_data.pop("reason", "No reason provided")
    
    was_delivered = record.status.lower() != "delivered"
    for key, value in update_data.items():
        setattr(record, key, value)
        
    is_delivered = record.status.lower() == "delivered"
    
    if was_delivered and is_delivered:
        if not record.delivered_time:
            record.delivered_time = datetime.now()
            
        from app.models.notification import Notification
        notification = Notification(
            type="success",
            title="Delivery Completed",
            message=f"Vehicle {record.vehicle_id} has been delivered successfully.",
            module="oem-portal",
            reference_id=str(record.id),
            target_url="/oem-portal",
        )
        db.add(notification)
        
        await manager.broadcast({
            "type": "NEW_NOTIFICATION",
            "data": {
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "type": notification.type,
                "target_url": notification.target_url
            }
        })

    db.commit()
    db.refresh(record)
    
    new_data = DispatchRecordResponse.model_validate(record).model_dump()
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "dispatch_record_updated", f"Dispatch Record #{record.id} updated",
        edited_by=getattr(current_user, "username", "System"),
        reason=reason, old_value=old_data, new_value=new_data
    )
    
    response_data = DispatchRecordResponse.model_validate(record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_RECORD_UPDATED",
        "data": response_data
    })
    return record
