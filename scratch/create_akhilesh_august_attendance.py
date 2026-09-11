from datetime import date, datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord
from app.services.attendance_engine import PayrollSyncEngine

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    if not worker:
        print("Worker ID 31 not found!")
    else:
        print(f"Updating August 2026 attendance for {worker.name} (ID: {worker.id})...")

        # 7 Present dates: Aug 1, 3, 4, 5, 6, 7, 8
        present_dates = {
            date(2026, 8, 1),
            date(2026, 8, 3),
            date(2026, 8, 4),
            date(2026, 8, 5),
            date(2026, 8, 6),
            date(2026, 8, 7),
            date(2026, 8, 8)
        }

        # Clear any existing August 2026 attendance for worker 31
        db.query(Attendance).filter(
            Attendance.worker_id == 31,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).delete()
        db.commit()

        # Create attendance for each day of August 2026 (31 days)
        created_records = []
        for day in range(1, 32):
            curr_date = date(2026, 8, day)
            is_present = curr_date in present_dates

            if is_present:
                p_in = datetime(2026, 8, day, 9, 15, 0)
                p_out = datetime(2026, 8, day, 18, 0, 0)
                status = "Present"
                net_hours = 8.0
                late_mins = 0
            else:
                p_in = None
                p_out = None
                status = "Absent"
                net_hours = 0.0
                late_mins = 0

            att = Attendance(
                worker_id=31,
                date=curr_date,
                status=status,
                punch_in=p_in,
                punch_out=p_out,
                net_working_hours=net_hours,
                late_minutes=late_mins,
                ot_hours=0.0
            )
            db.add(att)
            created_records.append(att)

        db.commit()
        print(f"Created {len(created_records)} attendance records for August 2026.")

        # Sync August Payroll for worker 31
        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == 31).first()
        if not profile:
            profile = SalaryProfile(worker_id=31, monthly_salary=10000.0)
            db.add(profile)
            db.commit()

        PayrollSyncEngine.sync_daily_attendance(db, created_records[-1], profile)

        payroll = db.query(PayrollRecord).filter(PayrollRecord.worker_id == 31, PayrollRecord.month == "2026-08").first()
        if payroll:
            print(f"\nAugust Payroll Updated Successfully:")
            print(f"- Days Present: {payroll.days_present}")
            print(f"- Days Absent: {payroll.days_absent}")
            print(f"- Base Salary: INR {payroll.base_salary}")
            print(f"- Net Working Days: {payroll.net_working_days}")
            print(f"- Final Salary: INR {payroll.final_salary}")

finally:
    db.close()
