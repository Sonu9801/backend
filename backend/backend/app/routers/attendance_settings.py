from fastapi import APIRouter, Depends, HTTPException
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.attendance_settings import AttendanceSettings
from app.schemas.attendance_settings import AttendanceSettingsUpdate, AttendanceSettingsResponse

router = APIRouter(prefix="/settings/attendance", tags=["settings"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=AttendanceSettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    settings = db.query(AttendanceSettings).first()
    if not settings:
        settings = AttendanceSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("", response_model=AttendanceSettingsResponse)
def update_settings(settings_in: AttendanceSettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(AttendanceSettings).first()
    if not settings:
        settings = AttendanceSettings()
        db.add(settings)
    
    for key, value in settings_in.model_dump().items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings

from app.models.shift import Shift
from app.models.holiday import Holiday
from app.schemas.attendance_settings import ShiftResponse, ShiftCreate, ShiftUpdate, HolidayResponse, HolidayCreate
from typing import List

@router.get("/shifts", response_model=List[ShiftResponse])
def get_shifts(db: Session = Depends(get_db)):
    return db.query(Shift).all()

@router.post("/shifts", response_model=ShiftResponse)
def create_shift(shift_in: ShiftCreate, db: Session = Depends(get_db)):
    db_shift = Shift(**shift_in.model_dump())
    db.add(db_shift)
    db.commit()
    db.refresh(db_shift)
    return db_shift

@router.put("/shifts/{shift_id}", response_model=ShiftResponse)
def update_shift(shift_id: int, shift_in: ShiftUpdate, db: Session = Depends(get_db)):
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    for key, value in shift_in.model_dump().items():
        setattr(db_shift, key, value)
    
    db.commit()
    db.refresh(db_shift)
    return db_shift

@router.delete("/shifts/{shift_id}")
def delete_shift(shift_id: int, db: Session = Depends(get_db)):
    db_shift = db.query(Shift).filter(Shift.id == shift_id).first()
    if not db_shift:
        raise HTTPException(status_code=404, detail="Shift not found")
    
    db.delete(db_shift)
    db.commit()
    return {"message": "Shift deleted"}

@router.get("/holidays", response_model=List[HolidayResponse])
def get_holidays(db: Session = Depends(get_db)):
    return db.query(Holiday).all()

@router.post("/holidays", response_model=HolidayResponse)
def create_holiday(holiday_in: HolidayCreate, db: Session = Depends(get_db)):
    db_holiday = Holiday(**holiday_in.model_dump())
    db.add(db_holiday)
    db.commit()
    db.refresh(db_holiday)
    return db_holiday

@router.delete("/holidays/{holiday_id}")
def delete_holiday(holiday_id: int, db: Session = Depends(get_db)):
    db_holiday = db.query(Holiday).filter(Holiday.id == holiday_id).first()
    if not db_holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
    
    db.delete(db_holiday)
    db.commit()
    return {"message": "Holiday deleted"}
