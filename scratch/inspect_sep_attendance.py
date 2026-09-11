from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    print(f"User: {worker.name} (ID: {worker.id})")
    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).order_by(Attendance.date.asc()).all()

    print(f"\nSeptember 2026 Attendance Records ({len(records)} found):")
    for r in records:
        print(f"Date: {r.date}, Status: {r.status}, Punch In: {r.punch_in}, Punch Out: {r.punch_out}, Net Working Hours: {r.net_working_hours}, OT Hours: {r.ot_hours}, Late Minutes: {r.late_minutes}")
finally:
    db.close()
