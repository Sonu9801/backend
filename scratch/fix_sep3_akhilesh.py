from datetime import date, datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).all()

    for r in records:
        if r.status == "Present":
            r.punch_in = datetime(r.date.year, r.date.month, r.date.day, 17, 30, 0)
            r.punch_out = datetime(r.date.year, r.date.month, r.date.day, 23, 0, 0)
            r.net_working_hours = 5.5
            r.ot_hours = 0.0
            r.late_minutes = 0

    db.commit()
    print(f"Updated {len(records)} September attendance records for {worker.name}!")

    records = db.query(Attendance).filter(
        Attendance.worker_id == 31,
        Attendance.date >= date(2026, 9, 1),
        Attendance.date <= date(2026, 9, 30)
    ).order_by(Attendance.date.asc()).all()

    for r in records:
        print(f"Date: {r.date}, Status: {r.status}, In: {r.punch_in.strftime('%I:%M %p')}, Out: {r.punch_out.strftime('%I:%M %p')}, NetHrs: {r.net_working_hours}h, OTHrs: {r.ot_hours}h")

finally:
    db.close()
