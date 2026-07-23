from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.routers.auth import get_current_active_user
from app.models.leave import LeaveRequest
from app.models.user import User

router = APIRouter(prefix="/leave", tags=["Leave"])

class LeaveRequestCreate(BaseModel):
    worker_id: int
    start_date: str
    end_date: str
    leave_type: str
    reason: Optional[str] = None

@router.post("/")
async def create_leave_request(payload: LeaveRequestCreate, db: Session = Depends(get_db)):
    start_val = datetime.strptime(payload.start_date, "%Y-%m-%d").date()
    end_val = datetime.strptime(payload.end_date, "%Y-%m-%d").date()
    
    req = LeaveRequest(
        worker_id=payload.worker_id,
        start_date=start_val,
        end_date=end_val,
        leave_type=payload.leave_type,
        reason=payload.reason
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    
    from app.services.websocket_manager import manager
    import asyncio
    asyncio.create_task(manager.broadcast({"type": "LEAVE_UPDATE", "data": {"worker_id": req.worker_id}}))
    
    return {"message": "Leave request submitted successfully", "id": req.id}

@router.get("/worker/{worker_id}")
def get_worker_leaves(worker_id: int, db: Session = Depends(get_db)):
    return db.query(LeaveRequest).filter(LeaveRequest.worker_id == worker_id).order_by(LeaveRequest.created_at.desc()).all()

@router.get("/")
def get_all_leaves(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(LeaveRequest).order_by(LeaveRequest.created_at.desc()).all()

class LeaveStatusUpdate(BaseModel):
    status: str
    remarks: Optional[str] = None

@router.put("/{leave_id}/status")
async def update_leave_status(leave_id: int, payload: LeaveStatusUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    req = db.query(LeaveRequest).filter(LeaveRequest.id == leave_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Leave request not found")
        
    req.status = payload.status
    req.admin_remarks = payload.remarks
    req.approved_by_id = current_user.id
    db.commit()
    
    if payload.status.lower() == "approved":
        from app.models.attendance import Attendance
        from app.models.salary_profile import SalaryProfile
        from app.services.attendance_engine import PayrollSyncEngine
        from datetime import timedelta
        
        sp = db.query(SalaryProfile).filter(SalaryProfile.worker_id == req.worker_id).first()
        
        curr_date = req.start_date
        while curr_date <= req.end_date:
            att = db.query(Attendance).filter(Attendance.worker_id == req.worker_id, Attendance.date == curr_date).first()
            if not att:
                att = Attendance(worker_id=req.worker_id, date=curr_date, status=req.leave_type)
                db.add(att)
            else:
                att.status = req.leave_type
            
            db.commit()
            db.refresh(att)
            PayrollSyncEngine.sync_daily_attendance(db, att, sp)
            
            curr_date += timedelta(days=1)
    
    # Broadcast to WebSocket
    from app.services.websocket_manager import manager
    import asyncio
    asyncio.create_task(manager.broadcast({"type": "LEAVE_UPDATE", "payload": {"worker_id": req.worker_id}}))
    asyncio.create_task(manager.broadcast({"type": "PAYROLL_UPDATE", "payload": {"worker_id": req.worker_id}}))
    asyncio.create_task(manager.broadcast({"type": "ATTENDANCE_UPDATE", "payload": {"worker_id": req.worker_id}}))
    
    return {"message": f"Leave {payload.status.lower()} successfully"}
