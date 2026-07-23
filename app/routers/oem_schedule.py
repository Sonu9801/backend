from fastapi import APIRouter, Depends
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.oem_schedule import OEMSchedule

router = APIRouter(prefix="/api/oem_schedule", tags=["OEM Schedule"], dependencies=[Depends(get_current_active_user)])

@router.get("/")
def get_oem_schedules(db: Session = Depends(get_db)):
    return db.query(OEMSchedule).all()
