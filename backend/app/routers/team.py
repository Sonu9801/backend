from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.routers.auth import get_current_active_user
from app.models.user import User
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest

router = APIRouter(prefix="/team", tags=["Team"])

@router.get("/summary/{manager_id}")
def get_team_summary(manager_id: int, db: Session = Depends(get_db)):
    # Mock finding team members
    # In a real app, we'd check manager_id or department
    today = datetime.now().strftime("%Y-%m-%d")
    workers = db.query(User).filter(User.employee_id.isnot(None), User.role == 'worker').all()
    worker_ids = [w.id for w in workers]
    
    attendances = db.query(Attendance).filter(Attendance.date == today, Attendance.worker_id.in_(worker_ids)).all()
    
    present = sum(1 for a in attendances if a.status in ['Present', 'Punched In'])
    absent = sum(1 for a in attendances if a.status == 'Absent')
    late = sum(1 for a in attendances if (a.late_minutes or 0) > 0)
    
    return {
        "total": len(workers),
        "present": present,
        "absent": absent,
        "late": late,
        "online_workers": [w.name for w in workers[:2]] # mock
    }

@router.get("/pending-requests/{manager_id}")
def get_pending_requests(manager_id: int, db: Session = Depends(get_db)):
    pending_leaves = db.query(LeaveRequest).filter(LeaveRequest.status == "Pending").count()
    return {
        "pending_leaves": pending_leaves,
        "pending_corrections": 0 # Mock for exceptions count
    }
