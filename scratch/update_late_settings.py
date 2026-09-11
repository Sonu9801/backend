from app.database import SessionLocal
from app.models.attendance_settings import AttendanceSettings
from app.models.attendance import Attendance
from app.services.attendance_engine import TimeEngine, PayrollSyncEngine
from app.models.salary_profile import SalaryProfile

db = SessionLocal()

try:
    settings = db.query(AttendanceSettings).first()
    if not settings:
        settings = AttendanceSettings(present_window_end="09:30:00")
        db.add(settings)
    else:
        settings.present_window_end = "09:30:00"
    db.commit()
    db.refresh(settings)
    print(f"AttendanceSettings updated: default_shift_start={settings.default_shift_start}, present_window_end={settings.present_window_end}")

    # Recalculate today's and recent attendance records if any
    attendances = db.query(Attendance).filter(Attendance.punch_in.isnot(None)).all()
    updated_count = 0
    for att in attendances:
        stats = TimeEngine.calculate_status(settings, punch_in=att.punch_in, punch_out=att.punch_out)
        att.late_minutes = stats.get("late_minutes", 0)
        if att.status not in ["Festival Work", "Sunday Work", "Holiday Work"]:
            att.status = stats.get("status", "Present")
        
        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == att.worker_id).first()
        if profile:
            PayrollSyncEngine.sync_daily_attendance(db, att, profile)
        updated_count += 1
    
    db.commit()
    print(f"Recalculated {updated_count} attendance records with 09:30 AM late threshold!")

finally:
    db.close()
