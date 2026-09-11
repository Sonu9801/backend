from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    users = db.query(User).filter(User.name.ilike("%akhilesh%")).all()
    print(f"Found {len(users)} users matching 'akhilesh':")
    for u in users:
        print(f"ID: {u.id}, Name: {u.name}, Role: {u.role}, Employee ID: {u.employee_id}")

    if users:
        worker = users[0]
        records = db.query(Attendance).filter(
            Attendance.worker_id == worker.id,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).order_by(Attendance.date.asc()).all()

        print(f"\nAugust 2026 attendance records for {worker.name} (Total {len(records)} records):")
        for r in records:
            print(f"Date: {r.date}, Status: {r.status}, Net Hours: {r.net_working_hours}, Punch In: {r.punch_in}, Punch Out: {r.punch_out}")
finally:
    db.close()
