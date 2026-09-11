from app.database import SessionLocal
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    sample = db.query(Attendance).filter(
        Attendance.date >= date(2026, 8, 1),
        Attendance.date <= date(2026, 8, 31)
    ).limit(10).all()

    print(f"Sample August 2026 records from other workers ({len(sample)} found):")
    for r in sample:
        print(f"WorkerID: {r.worker_id}, Date: {r.date}, Status: {r.status}, Net Hours: {r.net_working_hours}, PunchIn: {r.punch_in}, PunchOut: {r.punch_out}")
finally:
    db.close()
