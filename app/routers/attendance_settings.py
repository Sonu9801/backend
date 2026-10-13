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

from pydantic import BaseModel
from typing import Optional
from app.models.user import User

class BulkShiftUpdateRequest(BaseModel):
    shift_start: str
    shift_end: str
    shift_type: Optional[str] = "General Shift"
    present_window_end: Optional[str] = None
    half_day_start: Optional[str] = None
    update_global_settings: Optional[bool] = True

@router.post("/apply-to-all-workers")
def apply_shift_to_all_workers(
    payload: BulkShiftUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Applies new shift timings to all workers in one go and updates global attendance rules.
    """
    s_start = payload.shift_start
    s_end = payload.shift_end
    if len(s_start) == 5:
        s_start += ":00"
    if len(s_end) == 5:
        s_end += ":00"

    # Update global settings if requested
    if payload.update_global_settings:
        settings = db.query(AttendanceSettings).first()
        if not settings:
            settings = AttendanceSettings()
            db.add(settings)
        settings.default_shift_start = s_start
        settings.default_shift_end = s_end

        if payload.present_window_end:
            pw = payload.present_window_end
            settings.present_window_end = pw + ":00" if len(pw) == 5 else pw
        else:
            try:
                h, m = int(s_start.split(":")[0]), int(s_start.split(":")[1])
                m_total = h * 60 + m + 30
                settings.present_window_end = f"{(m_total // 60) % 24:02d}:{m_total % 60:02d}:00"
            except Exception:
                pass

        if payload.half_day_start:
            hd = payload.half_day_start
            settings.half_day_start = hd + ":00" if len(hd) == 5 else hd
        else:
            try:
                h, m = int(s_start.split(":")[0]), int(s_start.split(":")[1])
                m_total = h * 60 + m + 270 # 4.5 hours
                settings.half_day_start = f"{(m_total // 60) % 24:02d}:{m_total % 60:02d}:00"
            except Exception:
                pass

    # Update all workers
    updated_count = db.query(User).filter(User.role == "worker").update({
        User.shift_start: s_start,
        User.shift_end: s_end,
        User.shift_type: payload.shift_type
    })
    db.commit()

    return {
        "success": True,
        "message": f"Successfully updated shift timings for {updated_count} workers to {payload.shift_start} - {payload.shift_end}",
        "updated_workers": updated_count,
        "shift_start": s_start,
        "shift_end": s_end
    }

from datetime import date
from typing import List
from app.models.shift import Shift
from app.models.holiday import Holiday
from app.schemas.attendance_settings import ShiftResponse, ShiftCreate, ShiftUpdate, HolidayResponse, HolidayCreate

DEFAULT_HOLIDAYS_DATA = [
    # --- 2025 ---
    {"date": date(2025, 1, 1), "name": "New Year", "type": "National"},
    {"date": date(2025, 1, 26), "name": "Republic Day", "type": "National"},
    {"date": date(2025, 3, 14), "name": "Holi", "type": "Festival"},
    {"date": date(2025, 5, 1), "name": "Labour Day", "type": "National"},
    {"date": date(2025, 8, 9), "name": "Raksha Bandhan", "type": "Festival"},
    {"date": date(2025, 8, 15), "name": "Independence Day & Janmashtami", "type": "National"},
    {"date": date(2025, 9, 17), "name": "Vishwakarma Puja", "type": "Festival"},
    {"date": date(2025, 10, 2), "name": "Gandhi Jayanti & Dussehra", "type": "National"},
    {"date": date(2025, 10, 20), "name": "Diwali", "type": "Festival"},

    # --- 2026 ---
    {"date": date(2026, 1, 1), "name": "New Year", "type": "National"},
    {"date": date(2026, 1, 26), "name": "Republic Day", "type": "National"},
    {"date": date(2026, 3, 4), "name": "Holi", "type": "Festival"},
    {"date": date(2026, 5, 1), "name": "Labour Day", "type": "National"},
    {"date": date(2026, 8, 15), "name": "Independence Day", "type": "National"},
    {"date": date(2026, 8, 28), "name": "Raksha Bandhan", "type": "Festival"},
    {"date": date(2026, 9, 4), "name": "Janmashtami", "type": "Festival"},
    {"date": date(2026, 9, 17), "name": "Vishwakarma Puja", "type": "Festival"},
    {"date": date(2026, 10, 2), "name": "Gandhi Jayanti", "type": "National"},
    {"date": date(2026, 10, 20), "name": "Dussehra", "type": "Festival"},
    {"date": date(2026, 11, 8), "name": "Diwali", "type": "Festival"},

    # --- 2027 ---
    {"date": date(2027, 1, 1), "name": "New Year", "type": "National"},
    {"date": date(2027, 1, 26), "name": "Republic Day", "type": "National"},
    {"date": date(2027, 3, 22), "name": "Holi", "type": "Festival"},
    {"date": date(2027, 5, 1), "name": "Labour Day", "type": "National"},
    {"date": date(2027, 8, 15), "name": "Independence Day", "type": "National"},
    {"date": date(2027, 8, 17), "name": "Raksha Bandhan", "type": "Festival"},
    {"date": date(2027, 8, 25), "name": "Janmashtami", "type": "Festival"},
    {"date": date(2027, 9, 17), "name": "Vishwakarma Puja", "type": "Festival"},
    {"date": date(2027, 10, 2), "name": "Gandhi Jayanti", "type": "National"},
    {"date": date(2027, 10, 9), "name": "Dussehra", "type": "Festival"},
    {"date": date(2027, 10, 29), "name": "Diwali", "type": "Festival"},

    # --- 2028 ---
    {"date": date(2028, 1, 1), "name": "New Year", "type": "National"},
    {"date": date(2028, 1, 26), "name": "Republic Day", "type": "National"},
    {"date": date(2028, 3, 11), "name": "Holi", "type": "Festival"},
    {"date": date(2028, 5, 1), "name": "Labour Day", "type": "National"},
    {"date": date(2028, 8, 5), "name": "Raksha Bandhan", "type": "Festival"},
    {"date": date(2028, 8, 13), "name": "Janmashtami", "type": "Festival"},
    {"date": date(2028, 8, 15), "name": "Independence Day", "type": "National"},
    {"date": date(2028, 9, 17), "name": "Vishwakarma Puja", "type": "Festival"},
    {"date": date(2028, 9, 28), "name": "Dussehra", "type": "Festival"},
    {"date": date(2028, 10, 2), "name": "Gandhi Jayanti", "type": "National"},
    {"date": date(2028, 10, 17), "name": "Diwali", "type": "Festival"},
]

def auto_seed_holidays_if_empty(db: Session):
    existing = db.query(Holiday).all()
    if not existing:
        for item in DEFAULT_HOLIDAYS_DATA:
            db.add(Holiday(date=item["date"], name=item["name"], type=item["type"]))
        db.commit()

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
    auto_seed_holidays_if_empty(db)
    return db.query(Holiday).order_by(Holiday.date.asc()).all()

@router.post("/holidays/seed-defaults")
def seed_default_holidays(db: Session = Depends(get_db)):
    existing_dates = {h.date for h in db.query(Holiday).all()}
    added_count = 0
    for item in DEFAULT_HOLIDAYS_DATA:
        if item["date"] not in existing_dates:
            db.add(Holiday(date=item["date"], name=item["name"], type=item["type"]))
            added_count += 1
    db.commit()
    return {"message": f"Successfully seeded {added_count} holidays"}

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
