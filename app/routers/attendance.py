from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta, date, time
from app.database import get_db
from app.models.user import User
from app.models.attendance import Attendance, AttendanceLog, AttendanceException
from app.models.holiday import Holiday
from app.models.attendance_settings import AttendanceSettings
from app.models.salary_profile import SalaryProfile
from app.services.websocket_manager import manager
from app.services.attendance_engine import GeofenceEngine, TimeEngine, PayrollSyncEngine
import os
import shutil
import uuid

def to_ist(dt: datetime) -> Optional[datetime]:
    if not dt:
        return None
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ist_offset)
    return dt.astimezone(ist_offset)

router = APIRouter(prefix="/attendance", tags=["Attendance"], dependencies=[Depends(get_current_active_user)])

UPLOAD_DIR = "uploads/attendance_photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/punch")
async def punch_attendance(
    request: Request,
    worker_id: int = Form(...),
    action: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(None),
    address: str = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    settings = db.query(AttendanceSettings).first()
    if not settings:
        settings = AttendanceSettings()

    is_valid, geo_msg = GeofenceEngine.validate_punch(settings, latitude, longitude, accuracy)
    
    if not is_valid:
        from app.models.notification import Notification
        notification = Notification(
            type="error",
            title="Attendance Exception",
            message=f"Worker {worker.name} attempted to punch outside geofence. ({geo_msg})",
            module="attendance",
            reference_id=str(worker.id),
            target_url="/attendance",
        )
        db.add(notification)
        # Create an exception record
        exc = AttendanceException(
            worker_id=worker.id,
            date=datetime.now().date(),
            exception_type="Outside Geofence",
            notes=geo_msg
        )
        db.add(exc)
        db.commit()
        try:
            await manager.broadcast({"type": "NEW_NOTIFICATION"})
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=geo_msg)

    # Save photo if exists
    photo_url = None
    if photo:
        filename = f"{worker_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:6]}.jpg"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(photo.file, buffer)
        photo_url = f"/uploads/attendance_photos/{filename}"

    ist_offset = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now()
    today = now.date()

    # Prevent duplicate punches (if already punched in/out in the last 1 minute)
    last_log = db.query(AttendanceLog).filter(
        AttendanceLog.worker_id == worker.id,
        AttendanceLog.action == action
    ).order_by(AttendanceLog.timestamp.desc()).first()

    if last_log and last_log.timestamp:
        now_naive = now.replace(tzinfo=None)
        last_log_naive = last_log.timestamp.replace(tzinfo=None)
        if abs((now_naive - last_log_naive).total_seconds()) < 60:
            raise HTTPException(status_code=400, detail="Duplicate punch detected. Please try again later.")

    log = AttendanceLog(
        worker_id=worker.id,
        action=action,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        address=address,
        photo_url=photo_url,
        is_valid=is_valid,
        ip_address=request.client.host if request.client else "Unknown",
        device_info=request.headers.get("User-Agent", "Unknown"),
        timestamp=now
    )
    db.add(log)

    record = db.query(Attendance).filter(
        Attendance.worker_id == worker.id, 
        Attendance.date == today
    ).first()

    from app.models.holiday import Holiday
    hol = db.query(Holiday).filter(Holiday.date == today).first()
    is_sun = today.weekday() == 6

    if action.lower() == "punch in":
        record.punch_in = now
        record.punch_in_photo_url = photo_url
        record.punch_out = None
        record.punch_out_photo_url = None
        worker.status = "Active"
        
        stats = TimeEngine.calculate_status(settings, punch_in=now)
        record.late_minutes = stats.get("late_minutes", 0)
        
        if hol:
            record.status = "Festival Work"
        elif is_sun:
            record.status = "Sunday Work"
            record.is_sunday = True
        elif stats.get("status") == "Half Day":
            record.status = "Half Day"
            
    elif action.lower() == "punch out":
        if not record.punch_in:
            record.punch_in = now - timedelta(hours=9) # fallback if missed
        record.punch_out = now
        record.punch_out_photo_url = photo_url
        worker.status = "Offline"
        
        stats = TimeEngine.calculate_status(settings, punch_in=record.punch_in, punch_out=now)
        record.net_working_hours = stats.get("net_working_hours", 0.0)
        record.ot_hours = stats.get("ot_hours", 0.0)
        record.early_exit_minutes = stats.get("early_exit_minutes", 0)
        
        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == worker.id).first()
        if profile:
            PayrollSyncEngine.sync_daily_attendance(db, record, profile)

    db.commit()

    try:
        await manager.broadcast({"type": "ATTENDANCE_UPDATE", "data": {
            "worker_id": worker.id,
            "worker_name": worker.name,
            "action": action,
            "status": worker.status,
            "timestamp": now.isoformat()
        }})
    except Exception as e:
        print(f"[WebSocket Warning] Failed to broadcast attendance update: {e}")

    return {"message": f"Successfully {action}", "photo_url": photo_url}

@router.get("/worker/{worker_id}/summary")
def get_worker_summary(worker_id: int, db: Session = Depends(get_db)):
    today = datetime.now().date()
    record = db.query(Attendance).filter(
        Attendance.worker_id == worker_id, 
        Attendance.date == today
    ).first()

    if not record:
        return {
            "status": "Not Punched In",
            "net_working_hours": 0.0,
            "break_time": 0.0,
            "late_minutes": 0,
            "ot_hours": 0.0,
            "punch_in": None,
            "punch_out": None
        }

    return {
        "status": record.status or "Not Punched In",
        "net_working_hours": record.net_working_hours or 0.0,
        "break_time": record.break_time or 0.0,
        "late_minutes": record.late_minutes or 0,
        "ot_hours": record.ot_hours or 0.0,
        "punch_in": to_ist(record.punch_in).isoformat() if record.punch_in else None,
        "punch_out": to_ist(record.punch_out).isoformat() if record.punch_out else None
    }

@router.get("/worker/{worker_id}/history")
def get_worker_history(worker_id: int, month: Optional[str] = None, db: Session = Depends(get_db)):
    if month:
        import calendar
        try:
            y, m = map(int, month.split("-"))
            start_d = date(y, m, 1)
            _, max_d = calendar.monthrange(y, m)
            end_d = date(y, m, max_d)
            records = db.query(Attendance).filter(
                Attendance.worker_id == worker_id,
                Attendance.date >= start_d,
                Attendance.date <= end_d
            ).order_by(Attendance.date.desc()).all()
            return [
                {
                    "id": r.id,
                    "date": r.date.isoformat() if hasattr(r.date, 'isoformat') else str(r.date),
                    "status": r.status,
                    "punch_in": to_ist(r.punch_in).isoformat() if r.punch_in else None,
                    "punch_out": to_ist(r.punch_out).isoformat() if r.punch_out else None,
                    "net_working_hours": r.net_working_hours,
                    "ot_hours": r.ot_hours,
                    "late_minutes": r.late_minutes
                }
                for r in records
            ]
        except Exception:
            pass

    ninety_days_ago = datetime.now().date() - timedelta(days=90)
    records = db.query(Attendance).filter(
        Attendance.worker_id == worker_id,
        Attendance.date >= ninety_days_ago
    ).order_by(Attendance.date.desc()).all()
    
    return [
        {
            "id": r.id,
            "date": r.date.isoformat() if hasattr(r.date, 'isoformat') else str(r.date),
            "status": r.status,
            "punch_in": to_ist(r.punch_in).isoformat() if r.punch_in else None,
            "punch_out": to_ist(r.punch_out).isoformat() if r.punch_out else None,
            "net_working_hours": r.net_working_hours,
            "ot_hours": r.ot_hours,
            "late_minutes": r.late_minutes
        }
        for r in records
    ]

@router.get("/worker/{worker_id}/monthly-summary")
def get_worker_monthly_summary(worker_id: int, month: str = None, db: Session = Depends(get_db)):
    # month format: YYYY-MM
    target_date = datetime.strptime(month, "%Y-%m").date() if month else datetime.now().date()
    
    import calendar
    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    start_date = target_date.replace(day=1)
    end_date = target_date.replace(day=last_day)
    
    records = db.query(Attendance).filter(
        Attendance.worker_id == worker_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()
    
    summary = {
        "present_days": 0,
        "absent_days": 0,
        "half_days": 0,
        "leave_days": 0,
        "late_count": 0,
        "ot_hours": 0.0,
        "working_hours": 0.0,
        "sunday_work": 0,
        "holiday_work": 0,
        "net_attendance_percent": 0.0,
        "total_ot_hours": 0.0,
        "sunday_worked": 0
    }
    
    for r in records:
        status = (r.status or "").lower()
        if status == "present": summary["present_days"] += 1
        elif status == "absent": summary["absent_days"] += 1
        elif status == "half day": summary["half_days"] += 1
        elif status == "leave": summary["leave_days"] += 1
        
        if r.late_minutes and r.late_minutes > 0: summary["late_count"] += 1
        if r.ot_hours: summary["ot_hours"] += r.ot_hours
        if r.net_working_hours: summary["working_hours"] += r.net_working_hours
        if r.is_sunday: summary["sunday_work"] += 1

    # Virtual absences up to today
    record_map = {r.date if not isinstance(r.date, str) else datetime.strptime(str(r.date)[:10], "%Y-%m-%d").date(): r for r in records}
    from datetime import timedelta
    from app.models.holiday import Holiday
    today = datetime.now().date()
    holidays = db.query(Holiday).filter(Holiday.date >= start_date, Holiday.date <= end_date).all()
    holiday_dates = {h.date for h in holidays}
    
    curr_d = start_date
    limit_d = min(end_date, today)
    while curr_d <= limit_d:
        if curr_d not in record_map:
            is_sun = curr_d.weekday() == 6
            is_hol = curr_d in holiday_dates
            if not is_sun and not is_hol:
                summary["absent_days"] += 1
        curr_d += timedelta(days=1)
        
    summary["ot_hours"] = round(summary["ot_hours"], 1)
    summary["working_hours"] = round(summary["working_hours"], 1)
    summary["total_ot_hours"] = summary["ot_hours"]
    summary["sunday_worked"] = summary["sunday_work"]

    total_working_days = summary["present_days"] + summary["absent_days"] + summary["half_days"] + summary["leave_days"]
    if total_working_days > 0:
        summary["net_attendance_percent"] = round((summary["present_days"] + (summary["half_days"] * 0.5)) / total_working_days * 100, 1)
        
    return summary

@router.get("/worker/{worker_id}/full-month-logs")
def get_worker_full_month_logs(worker_id: int, month: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns complete day-by-day attendance for a worker for a specific month (1st day to last day of month).
    Fills empty/unpunched days so every single date in the month is listed with status and details.
    """
    import calendar
    today = datetime.now().date()
    if month:
        try:
            year, m = map(int, month.split("-"))
            target_date = date(year, m, 1)
        except Exception:
            target_date = today.replace(day=1)
    else:
        target_date = today.replace(day=1)

    _, last_day = calendar.monthrange(target_date.year, target_date.month)
    start_date = target_date.replace(day=1)
    end_date = target_date.replace(day=last_day)

    records = db.query(Attendance).filter(
        Attendance.worker_id == worker_id,
        Attendance.date >= start_date,
        Attendance.date <= end_date
    ).all()

    record_map = {r.date: r for r in records}

    holidays_db = db.query(Holiday).filter(
        Holiday.date >= start_date,
        Holiday.date <= end_date
    ).all()
    holiday_map = {h.date: h.name for h in holidays_db}

    days_list = []
    curr = start_date
    while curr <= end_date:
        rec = record_map.get(curr)
        is_sun = curr.weekday() == 6
        holiday_name = holiday_map.get(curr)

        if rec:
            is_non_working = rec.status in ["Absent", "Leave", "Holiday", "Not Punched", "Sunday"]
            status_val = rec.status or ("Sunday Work" if rec.is_sunday else ("Holiday" if is_sun else "Present"))
            if holiday_name:
                if rec.punch_in or (rec.net_working_hours and rec.net_working_hours > 0) or rec.status in ["Present", "Half Day", "Sunday Work", "Festival Work", "Holiday Work"]:
                    status_val = "Festival Work"
                    is_non_working = False
                else:
                    status_val = f"Holiday: {holiday_name}"

            days_list.append({
                "id": rec.id,
                "date": curr.isoformat(),
                "day_name": curr.strftime("%a"),
                "status": status_val,
                "holiday_name": holiday_name,
                "punch_in": None if is_non_working else (to_ist(rec.punch_in).strftime("%I:%M %p") if rec.punch_in else None),
                "punch_out": None if is_non_working else (to_ist(rec.punch_out).strftime("%I:%M %p") if rec.punch_out else None),
                "punch_in_full": None if is_non_working else (to_ist(rec.punch_in).isoformat() if rec.punch_in else None),
                "punch_out_full": None if is_non_working else (to_ist(rec.punch_out).isoformat() if rec.punch_out else None),
                "net_working_hours": 0.0 if is_non_working else (rec.net_working_hours or 0.0),
                "ot_hours": 0.0 if is_non_working else (rec.ot_hours or 0.0),
                "late_minutes": rec.late_minutes or 0,
                "is_sunday": bool(rec.is_sunday),
                "is_calendar_sunday": is_sun,
                "has_record": True
            })
        else:
            if holiday_name:
                default_status = f"Holiday: {holiday_name}"
            elif is_sun:
                default_status = "Holiday"
            else:
                default_status = "Not Punched" if curr <= today else "Upcoming"
            days_list.append({
                "id": None,
                "date": curr.isoformat(),
                "day_name": curr.strftime("%a"),
                "status": default_status,
                "holiday_name": holiday_name,
                "punch_in": None,
                "punch_out": None,
                "punch_in_full": None,
                "punch_out_full": None,
                "net_working_hours": 0.0,
                "ot_hours": 0.0,
                "late_minutes": 0,
                "is_sunday": False,
                "is_calendar_sunday": is_sun,
                "has_record": False
            })
        curr += timedelta(days=1)

    return days_list

class MarkDayAttendanceSchema(BaseModel):
    worker_id: int
    date: str # "YYYY-MM-DD"
    status: str # "Present", "Absent", "Half Day", "Leave", "Late", "Sunday Work", "Holiday"
    punch_in_time: Optional[str] = None # "HH:MM" e.g. "09:30"
    punch_out_time: Optional[str] = None # "HH:MM" e.g. "18:00"
    net_working_hours: Optional[float] = 0.0
    ot_hours: Optional[float] = 0.0
    is_sunday: Optional[bool] = False
    reason: Optional[str] = "Manual update by Admin/Manager"

@router.post("/mark-day")
async def mark_or_update_day_attendance(
    payload: MarkDayAttendanceSchema,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    if current_user.role not in ["owner", "admin", "manager", "supervisor", "finance_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit attendance")

    try:
        date_val = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    record = db.query(Attendance).filter(
        Attendance.worker_id == payload.worker_id,
        Attendance.date == date_val
    ).first()

    # Parse punch times (naive datetime for local storage)
    punch_in_dt = None
    if payload.punch_in_time and payload.punch_in_time.strip():
        try:
            time_str = payload.punch_in_time.strip()
            if "AM" in time_str.upper() or "PM" in time_str.upper():
                dt_obj = datetime.strptime(time_str.upper(), "%I:%M %p").time()
            else:
                h, m = map(int, time_str.split(":")[:2])
                dt_obj = time(h, m)
            punch_in_dt = datetime.combine(date_val, dt_obj)
        except Exception:
            pass

    punch_out_dt = None
    if payload.punch_out_time and payload.punch_out_time.strip():
        try:
            time_str = payload.punch_out_time.strip()
            if "AM" in time_str.upper() or "PM" in time_str.upper():
                dt_obj = datetime.strptime(time_str.upper(), "%I:%M %p").time()
            else:
                h, m = map(int, time_str.split(":")[:2])
                dt_obj = time(h, m)
            punch_out_dt = datetime.combine(date_val, dt_obj)
        except Exception:
            pass

    is_non_working = payload.status in ["Absent", "Leave", "Holiday", "Not Punched", "Sunday"]

    if is_non_working:
        punch_in_dt = None
        punch_out_dt = None
        working_to_save = 0.0
        ot_to_save = 0.0
    else:
        # Auto-calculate OT ONLY if punch_out is at or after 18:00 (6:00 PM threshold - 30m after 17:30 shift end)
        calculated_ot = 0.0
        if punch_in_dt and punch_out_dt:
            min_ot_start_dt = datetime.combine(date_val, time(18, 0))
            shift_end_dt = datetime.combine(date_val, time(17, 30))
            if punch_out_dt >= min_ot_start_dt:
                ot_seconds = (punch_out_dt - shift_end_dt).total_seconds()
                calculated_ot = round(ot_seconds / 3600.0, 1)

        ot_to_save = payload.ot_hours if (payload.ot_hours and payload.ot_hours > 0) else calculated_ot
        working_to_save = payload.net_working_hours if (payload.net_working_hours and payload.net_working_hours > 0) else 8.0

    is_sun = bool(payload.is_sunday or payload.status == "Sunday Work")

    if not record:
        record = Attendance(
            worker_id=payload.worker_id,
            date=date_val,
            status=payload.status,
            punch_in=punch_in_dt,
            punch_out=punch_out_dt,
            net_working_hours=working_to_save,
            ot_hours=ot_to_save,
            is_sunday=is_sun
        )
        db.add(record)
    else:
        record.status = payload.status
        record.punch_in = punch_in_dt
        record.punch_out = punch_out_dt
        record.net_working_hours = working_to_save
        record.ot_hours = ot_to_save
        if payload.is_sunday is not None: record.is_sunday = payload.is_sunday

    db.commit()
    db.refresh(record)

    # Sync Payroll
    from app.services.attendance_engine import PayrollSyncEngine
    from app.models.salary_profile import SalaryProfile
    sp = db.query(SalaryProfile).filter(SalaryProfile.worker_id == payload.worker_id).first()
    if sp:
        PayrollSyncEngine.sync_daily_attendance(db, record, sp)

    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "attendance_marked_manually", f"Attendance for worker {payload.worker_id} on {payload.date} set to {payload.status}",
        edited_by=getattr(current_user, "username", "Admin"),
        reason=payload.reason or "Manual Admin Edit", worker_id=payload.worker_id
    )

    # Send Notification to Worker
    try:
        from app.models.notification import Notification
        notif = Notification(
            user_id=payload.worker_id,
            title="Attendance Record Updated",
            message=f"Your attendance for {payload.date} has been updated to '{payload.status}' by {getattr(current_user, 'name', 'Admin')}.",
            module="attendance",
            target_url="/attendance",
            is_read=False
        )
        db.add(notif)
        db.commit()
    except Exception as n_err:
        print(f"[Notif Warning] Could not send attendance notification: {n_err}")

    # Broadcast WebSocket event to live update PWA app
    try:
        await manager.broadcast({
            "type": "ATTENDANCE_UPDATE",
            "payload": {
                "worker_id": payload.worker_id,
                "date": payload.date,
                "status": payload.status
            }
        })
        await manager.broadcast({
            "type": "NEW_NOTIFICATION",
            "payload": {"user_id": payload.worker_id}
        })
    except Exception as ws_err:
        print(f"[WebSocket Warning] Failed to broadcast attendance update: {ws_err}")

    return {"message": "Attendance marked successfully", "record_id": record.id}

@router.get("/")
def get_attendance(db: Session = Depends(get_db)):
    return db.query(Attendance).all()

@router.get("/logs/detailed")
def get_detailed_logs(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from sqlalchemy import or_, and_
    from datetime import date as date_type
    query = db.query(Attendance).join(User, Attendance.worker_id == User.id)
    if getattr(user, "role", None) == "supervisor":
        query = query.filter(User.department == getattr(user, "department", None))

    if search:
        query = query.filter(
            or_(
                User.name.ilike(f"%{search}%"),
                User.employee_id.ilike(f"%{search}%"),
                User.department.ilike(f"%{search}%"),
            )
        )
    if status and status != "All":
        query = query.filter(Attendance.status == status)
    if department and department != "All":
        query = query.filter(User.department == department)
    if date_from:
        query = query.filter(Attendance.date >= date_from)
    if date_to:
        query = query.filter(Attendance.date <= date_to)

    total = query.count()
    total_pages = max(1, -(-total // page_size))
    offset = (page - 1) * page_size
    records = query.order_by(Attendance.date.desc(), Attendance.id.desc()).offset(offset).limit(page_size).all()

    # Bulk fetch logs to avoid N+1 query problem
    worker_ids = list({r.worker_id for r in records if r.worker_id})
    min_date = min([r.date for r in records if r.date] + [date_type.max])
    max_date = max([r.date for r in records if r.date] + [date_type.min])

    logs_by_worker = {}
    if worker_ids and min_date != date_type.max:
        from datetime import datetime, timedelta
        start_ts = datetime.combine(min_date, datetime.min.time()) - timedelta(days=1)
        end_ts = datetime.combine(max_date, datetime.max.time()) + timedelta(days=1)
        
        all_logs = db.query(AttendanceLog).filter(
            AttendanceLog.worker_id.in_(worker_ids),
            AttendanceLog.timestamp >= start_ts,
            AttendanceLog.timestamp <= end_ts
        ).all()
        
        for lg in all_logs:
            if lg.worker_id not in logs_by_worker:
                logs_by_worker[lg.worker_id] = []
            logs_by_worker[lg.worker_id].append(lg)
            
        # Sort logs by timestamp for accurate first() lookup
        for wid in logs_by_worker:
            logs_by_worker[wid].sort(key=lambda x: x.timestamp)

    results = []
    for r in records:
        worker = r.worker
        if worker:
            w_logs = logs_by_worker.get(worker.id, [])
            in_log = next((lg for lg in w_logs if lg.action == "Punch In" and lg.timestamp >= r.punch_in), None) if r.punch_in else None
            out_log = next((lg for lg in w_logs if lg.action == "Punch Out" and lg.timestamp >= r.punch_out), None) if r.punch_out else None

            results.append({
                "id": r.id,
                "worker_id": worker.id,
                "employee_name": worker.name,
                "employee_id": worker.employee_id,
                "department": worker.department,
                "date": r.date.isoformat() if r.date else None,
                "punch_in": to_ist(r.punch_in).isoformat() if r.punch_in else None,
                "punch_out": to_ist(r.punch_out).isoformat() if r.punch_out else None,
                "status": r.status,
                "net_working_hours": r.net_working_hours,
                "ot_hours": r.ot_hours,
                "late_minutes": r.late_minutes,
                "is_sunday": r.is_sunday,
                "location_status": "Verified",
                "photo_status": "Verified" if r.punch_in_photo_url or r.punch_out_photo_url else "Pending",
                "punch_in_photo_url": r.punch_in_photo_url,
                "punch_out_photo_url": r.punch_out_photo_url,
                "device_info": in_log.device_info if in_log else (out_log.device_info if out_log else "Unknown"),
                "ip_address": in_log.ip_address if in_log else (out_log.ip_address if out_log else "Unknown"),
                "latitude": in_log.latitude if in_log else (out_log.latitude if out_log else None),
                "longitude": in_log.longitude if in_log else (out_log.longitude if out_log else None),
            })

    return {
        "items": results,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/exceptions")
def get_exceptions(db: Session = Depends(get_db)):
    return db.query(AttendanceException).all()

@router.post("/exceptions")
def create_exception(worker_id: int, date_str: str, type: str, notes: str, db: Session = Depends(get_db)):
    date_val = datetime.strptime(date_str, "%Y-%m-%d").date()
    exc = AttendanceException(
        worker_id=worker_id,
        date=date_val,
        exception_type=type,
        notes=notes
    )
    db.add(exc)
    db.commit()
    return {"message": "Exception logged successfully"}

from pydantic import BaseModel

class ApproveExceptionPayload(BaseModel):
    reason: str

@router.put("/exceptions/{id}/approve")
async def approve_exception(id: int, payload: ApproveExceptionPayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    exc = db.query(AttendanceException).filter(AttendanceException.id == id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
        
    old_status = exc.status
    exc.status = "Approved"
    db.commit()
    db.refresh(exc)
    
    # Process the correction on the attendance record
    att = db.query(Attendance).filter(Attendance.worker_id == exc.worker_id, Attendance.date == exc.date).first()
    if att:
        if exc.exception_type == "Forgot Punch In":
            # For simplicity, we just set a default punch in
            from datetime import time
            ist_offset = timezone(timedelta(hours=5, minutes=30))
            att.punch_in = datetime.combine(exc.date, time(9, 0)).replace(tzinfo=ist_offset)
            att.status = "Present"
        elif exc.exception_type == "Forgot Punch Out":
            from datetime import time
            ist_offset = timezone(timedelta(hours=5, minutes=30))
            att.punch_out = datetime.combine(exc.date, time(18, 0)).replace(tzinfo=ist_offset)
            att.net_working_hours = 9.0
            
        db.commit()
        
        # Sync Payroll
        from app.services.attendance_engine import PayrollSyncEngine
        from app.models.salary_profile import SalaryProfile
        sp = db.query(SalaryProfile).filter(SalaryProfile.worker_id == exc.worker_id).first()
        PayrollSyncEngine.sync_daily_attendance(db, att, sp)
        
        from app.routers.websocket import manager
        import asyncio
        asyncio.create_task(manager.broadcast({"type": "ATTENDANCE_UPDATE", "payload": {"worker_id": exc.worker_id}}))
    
    from app.services.audit import log_audit_event
    
    await log_audit_event(
        db, "exception_approved", f"Exception {exc.exception_type} approved for Worker {exc.worker_id}",
        edited_by=getattr(current_user, "username", "System"),
        reason=payload.reason, old_value={"status": old_status}, new_value={"status": "Approved"}, worker_id=exc.worker_id
    )
    
    return {"message": "Exception approved and payroll synced"}

from pydantic import BaseModel
from typing import Optional

class AttendanceUpdatePayload(BaseModel):
    status: Optional[str] = None
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    net_working_hours: Optional[float] = None
    ot_hours: Optional[float] = None
    late_minutes: Optional[int] = None
    reason: str

@router.put("/{id}")
async def update_attendance(id: int, payload: AttendanceUpdatePayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    if current_user.role not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    record = db.query(Attendance).filter(Attendance.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
        
    # Build old data dictionary manually since it's not a Pydantic model directly
    old_data = {
        "status": record.status,
        "punch_in": to_ist(record.punch_in).isoformat() if record.punch_in else None,
        "punch_out": to_ist(record.punch_out).isoformat() if record.punch_out else None,
        "net_working_hours": record.net_working_hours,
        "ot_hours": record.ot_hours,
        "late_minutes": record.late_minutes
    }
    
    if payload.status is not None: record.status = payload.status
    if payload.punch_in is not None: record.punch_in = payload.punch_in
    if payload.punch_out is not None: record.punch_out = payload.punch_out
    if payload.net_working_hours is not None: record.net_working_hours = payload.net_working_hours
    if payload.ot_hours is not None: record.ot_hours = payload.ot_hours
    if payload.late_minutes is not None: record.late_minutes = payload.late_minutes
    
    db.commit()
    db.refresh(record)
    
    new_data = {
        "status": record.status,
        "punch_in": to_ist(record.punch_in).isoformat() if record.punch_in else None,
        "punch_out": to_ist(record.punch_out).isoformat() if record.punch_out else None,
        "net_working_hours": record.net_working_hours,
        "ot_hours": record.ot_hours,
        "late_minutes": record.late_minutes
    }
    
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "attendance_updated", f"Attendance updated for worker {record.worker_id}",
        edited_by=getattr(current_user, "username", "System"),
        reason=payload.reason, old_value=old_data, new_value=new_data, worker_id=record.worker_id
    )
    
    return {"message": "Attendance updated"}

@router.delete("/{id}")
async def delete_attendance(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    if current_user.role not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    record = db.query(Attendance).filter(Attendance.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
        
    worker_id = record.worker_id
    db.delete(record)
    db.commit()
    
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "attendance_deleted", f"Attendance deleted for worker {worker_id}",
        edited_by=getattr(current_user, "username", "System"),
        reason="Manual Deletion", worker_id=worker_id
    )
    
    return {"message": "Attendance record deleted"}


@router.get("/analytics")
def get_analytics(
    user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    now = datetime.now()
    today = now.date()
    
    query_workers = db.query(User).filter(User.employee_id.isnot(None))
    query_today = db.query(Attendance).filter(Attendance.date == today)
    
    if getattr(user, "role", None) == "supervisor":
        query_workers = query_workers.filter(User.department == getattr(user, "department", None))
        query_today = query_today.join(User).filter(User.department == getattr(user, "department", None))

    all_workers = query_workers.all()
    total_workers = len(all_workers)
    today_records = query_today.all()
    
    present = 0
    absent = 0
    late = 0
    half_day = 0
    total_hours = 0
    punch_count = db.query(AttendanceLog).filter(
        func.date(AttendanceLog.timestamp) == today
    ).count()
    
    # Department Stats map
    dept_map = {}
    for w in all_workers:
        dept = w.department or "Unknown"
        if dept not in dept_map:
            dept_map[dept] = {"name": dept, "present": 0, "absent": 0, "ot": 0, "total": 0}
        dept_map[dept]["total"] += 1
        
    for r in today_records:
        dept = r.worker.department if r.worker and r.worker.department else "Unknown"
        if dept not in dept_map:
            dept_map[dept] = {"name": dept, "present": 0, "absent": 0, "ot": 0, "total": 1}
            
        if r.status == "Present":
            present += 1
            dept_map[dept]["present"] += 1
        elif r.status == "Absent":
            absent += 1
            dept_map[dept]["absent"] += 1
        elif r.status == "Half Day":
            half_day += 1
            dept_map[dept]["present"] += 1
            
        if r.late_minutes and r.late_minutes > 0:
            late += 1
        if r.net_working_hours:
            total_hours += r.net_working_hours
        if r.ot_hours and r.ot_hours > 0:
            dept_map[dept]["ot"] += 1
            
    # Calculate absences for workers without records today
    recorded_worker_ids = {r.worker_id for r in today_records}
    for w in all_workers:
        if w.id not in recorded_worker_ids:
            absent += 1
            dept = w.department or "Unknown"
            dept_map[dept]["absent"] += 1
    
    avg_hours = total_hours / present if present > 0 else 0
    dept_stats_list = list(dept_map.values())
    
    # 7-day trend
    trend = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        day_records = db.query(Attendance).filter(Attendance.date == d)
        if getattr(user, "role", None) == "supervisor":
            day_records = day_records.join(User).filter(User.department == getattr(user, "department", None))
        
        day_present = 0
        day_late = 0
        for r in day_records.all():
            if r.status in ["Present", "Half Day"]:
                day_present += 1
            if r.late_minutes and r.late_minutes > 0:
                day_late += 1
        
        day_absent = total_workers - day_present
        trend.append({
            "day": d.strftime("%a"),
            "present": day_present,
            "absent": day_absent,
            "late": day_late
        })
    
    return {
        "present": present,
        "absent": absent,
        "late": late,
        "half_day": half_day,
        "total": total_workers,
        "average_working_hours": round(avg_hours, 1),
        "today_punch_count": punch_count,
        "ot_running": sum(d["ot"] for d in dept_stats_list),
        "attendance_trend": trend,
        "dept_stats": dept_stats_list
    }

