import os
import sys
import random
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.worker import Worker
from app.models.salary_profile import SalaryProfile
from app.models.attendance import Attendance
from app.models.payroll import AdvanceRequest

def seed():
    db = SessionLocal()
    
    existing = db.query(Worker).count()
        
    depts = ["Fabrication", "Paint", "Dispatch", "Quality", "Assembly"]
    roles = ["Operator", "Technician", "Supervisor", "Helper", "Inspector"]
    
    current_month = datetime.now().strftime("%Y-%m")
    year, month = map(int, current_month.split("-"))
    
    workers = []
    
    if existing < 15:
        print("Generating Workers...")
        for i in range(existing + 1, 16):
            w = Worker(
                employee_id=f"EMP-2026-{i:03d}",
                name=f"Demo Employee {i}",
                mobile_number=f"9876543{i:03d}",
                password="1234",
                department=random.choice(depts),
                role=random.choice(roles),
                employment_status="Active"
            )
            db.add(w)
            workers.append(w)
        db.commit()
    
    workers = db.query(Worker).all()

    print("Generating Salary Profiles...")
    for w in workers:
        if not db.query(SalaryProfile).filter_by(worker_id=w.id).first():
            is_monthly = random.choice([True, False])
            sp = SalaryProfile(
                worker_id=w.id,
                salary_type="Monthly" if is_monthly else "DailyWage",
                monthly_salary=random.randint(15000, 45000) if is_monthly else None,
                daily_wage=None if is_monthly else random.randint(500, 1500),
                ot_rate_per_hour=random.randint(100, 250),
                sunday_rate_per_hour=random.randint(150, 300)
            )
            db.add(sp)
    db.commit()

    print("Generating Attendance...")
    
    # 6 months of data
    start_date = datetime(year, month, 1) - timedelta(days=180)
    end_date = datetime.now()
    
    for w in workers:
        for day in range((end_date - start_date).days + 1):
            curr_date = start_date + timedelta(days=day)
            
            # Skip if already exists
            if db.query(Attendance).filter_by(worker_id=w.id, date=curr_date.date()).first():
                continue
                
            status_opts = ["Present"] * 70 + ["Absent"] * 10 + ["Half Day"] * 20
            st = random.choice(status_opts)
            
            ot_hrs = 0.0
            if st == "Present" and random.random() > 0.6:
                ot_hrs = float(random.choice([2.0, 3.0, 4.0]))
                
            att = Attendance(
                worker_id=w.id,
                date=curr_date.date(),
                status=st,
                ot_hours=ot_hrs,
                is_sunday=(curr_date.weekday() == 6)
            )
            db.add(att)
    db.commit()
    
    print("Generating Advances...")
    for w in workers[:7]: # 7 workers have advances
        if not db.query(AdvanceRequest).filter_by(worker_id=w.id).first():
            adv = AdvanceRequest(
                worker_id=w.id,
                amount=float(random.choice([1000, 2000, 5000])),
                reason="Medical Emergency" if random.random() > 0.5 else "Festival Bonus",
                status="Approved" if random.random() > 0.3 else "Pending",
                request_date=datetime.now() - timedelta(days=random.randint(1, 10))
            )
            db.add(adv)
    db.commit()
    
    print("Demo Data Successfully Generated!")

if __name__ == "__main__":
    seed()
