import sys
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import random
from app.database import SessionLocal, engine, Base
from app.models.worker import Worker
from app.models.attendance import Attendance, AttendanceLog
from app.models.salary_profile import SalaryProfile
from app.models.oem_schedule import OEMSchedule

def seed_advanced_data(db: Session):
    print("Seeding advanced data (Attendance, Payroll, OEM Schedules)...")
    
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    workers = db.query(Worker).all()
    if not workers:
        print("No workers found. Please run seed.py first.")
        return

    now = datetime.now(timezone.utc)
    
    # 1. Salary Profiles
    for worker in workers:
        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == worker.id).first()
        if not profile:
            profile = SalaryProfile(
                worker_id=worker.id,
                salary_type="Monthly" if worker.department in ["Engineering", "Quality"] else "DailyWage",
                monthly_salary=random.randint(40000, 80000) if worker.department in ["Engineering", "Quality"] else None,
                daily_wage=None if worker.department in ["Engineering", "Quality"] else random.randint(800, 1500),
                ot_rate_per_hour=random.randint(150, 300)
            )
            db.add(profile)
    
    # 2. Attendance & Logs
    for worker in workers:
        # Simulate last 5 days
        for i in range(5):
            day = (now - timedelta(days=i)).date()
            record = db.query(Attendance).filter(Attendance.worker_id == worker.id, Attendance.date == day).first()
            if not record:
                record = Attendance(
                    worker_id=worker.id,
                    date=day,
                    punch_in=now - timedelta(days=i, hours=8),
                    punch_out=now - timedelta(days=i),
                    status="Present" if i != 2 else "Absent",
                    ot_hours=random.choice([0.0, 0.0, 2.0, 3.5]),
                    is_sunday=False
                )
                db.add(record)
                
                # Add log
                log_in = AttendanceLog(
                    worker_id=worker.id,
                    action="Punch In",
                    latitude=19.0760 + random.uniform(-0.001, 0.001),
                    longitude=72.8777 + random.uniform(-0.001, 0.001),
                    is_valid=True,
                    timestamp=record.punch_in
                )
                db.add(log_in)

    # 3. OEM Schedules
    oems = [
        {"name": "Tata Power", "dealer": "Tata EV Solutions", "category": "Cargo Box", "qty": 150, "days_offset": 5},
        {"name": "Bajaj Auto", "dealer": "Bajaj Commute", "category": "Telecom Enclosure", "qty": 80, "days_offset": 2},
        {"name": "Mahindra Electric", "dealer": "Mahindra Mobility", "category": "Battery Box", "qty": 200, "days_offset": -1},
    ]
    
    for o in oems:
        sched = OEMSchedule(
            oem_name=o["name"],
            dealer_name=o["dealer"],
            expected_date=now + timedelta(days=o["days_offset"]),
            quantity=o["qty"],
            product_category=o["category"],
            status="Pending" if o["days_offset"] > 0 else "Delayed"
        )
        db.add(sched)

    db.commit()
    print("Successfully seeded advanced data!")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_advanced_data(db)
    finally:
        db.close()
