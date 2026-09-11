from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).order_by(Attendance.date.asc()).all()

    print(f"Total September records for worker 31: {len(records)}")
    for r in records:
        print(f"ID: {r.id}, Date: {r.date}, Status: {r.status}, In: {r.punch_in}, Out: {r.punch_out}, NetHrs: {r.net_working_hours}, OTHrs: {r.ot_hours}, LateMins: {r.late_minutes}")
finally:
    db.close()
