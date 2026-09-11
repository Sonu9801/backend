from datetime import date, datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord
from app.services.attendance_engine import TimeEngine, PayrollSyncEngine

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    settings = None
    from app.models.attendance_settings import AttendanceSettings
    settings = db.query(AttendanceSettings).first()

    # Recalculate/Fix September attendance records for worker 31
    sep_records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).all()

    print(f"Updating {len(sep_records)} September attendance records for {worker.name}...")

    for r in sep_records:
        if r.status == "Present":
            # Set to Evening Shift times: 05:30 PM (17:30) to 11:00 PM (23:00)
            r.punch_in = datetime(r.date.year, r.date.month, r.date.day, 17, 30, 0)
            r.punch_out = datetime(r.date.year, r.date.month, r.date.day, 23, 0, 0)
            r.net_working_hours = 5.5
            r.ot_hours = 0.0
            r.late_minutes = 0

    db.commit()
    print("September attendance records updated successfully!")

    # Verify updated records
    sep_records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).order_by(Attendance.date.asc()).all()

    for r in sep_records:
        print(f"Date: {r.date}, Status: {r.status}, In: {r.punch_in}, Out: {r.punch_out}, NetHrs: {r.net_working_hours}h, OTHrs: {r.ot_hours}h")

finally:
    db.close()
