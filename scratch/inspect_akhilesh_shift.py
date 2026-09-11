from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    print("User table columns for Akhilesh Sharma:")
    for col in worker.__table__.columns:
        val = getattr(worker, col.name)
        if "shift" in col.name.lower() or col.name in ["name", "role", "employee_id", "department"]:
            print(f"  {col.name}: {val}")

    print("\nAugust 2026 Attendance Records for Akhilesh Sharma (first 10):")
    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 8, 1),
        Attendance.date <= date(2026, 8, 31)
    ).order_by(Attendance.date.asc()).limit(10).all()

    for r in records:
        print(f"Date: {r.date}, Status: {r.status}, Punch In: {r.punch_in}, Punch Out: {r.punch_out}, Net Hours: {r.net_working_hours}")
finally:
    db.close()
