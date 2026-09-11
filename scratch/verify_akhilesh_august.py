from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 8, 1),
        Attendance.date <= date(2026, 8, 31)
    ).order_by(Attendance.date.asc()).all()

    present_list = [r for r in records if r.status == "Present"]
    absent_list = [r for r in records if r.status == "Absent"]

    print(f"Total August Records for {worker.name}: {len(records)}")
    print(f"Present Days ({len(present_list)}): {[r.date.strftime('%Y-%m-%d') for r in present_list]}")
    print(f"Absent Days Count: {len(absent_list)}")
finally:
    db.close()
