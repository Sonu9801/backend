from datetime import date, datetime
from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord
from app.models.holiday import Holiday
from app.services.attendance_engine import PayrollSyncEngine

db = SessionLocal()

try:
    holidays_db = db.query(Holiday).filter(
        Holiday.date >= date(2026, 8, 1),
        Holiday.date <= date(2026, 8, 31)
    ).all()
    holiday_dates = {h.date: h.name for h in holidays_db}

    target_user_ids = [32, 5]  # User ID 32: 'Sonu Kumar ', User ID 5: 'Sonu'

    for uid in target_user_ids:
        worker = db.query(User).filter(User.id == uid).first()
        if not worker:
            continue

        print(f"Updating August 2026 attendance to ALL PRESENT for {worker.name} (ID: {worker.id}, EmpID: {worker.employee_id})...")

        # Clear existing August attendance
        db.query(Attendance).filter(
            Attendance.worker_id == uid,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).delete()
        db.commit()

        created_records = []
        for day in range(1, 32):
            curr_d = date(2026, 8, day)
            is_sun = curr_d.weekday() == 6
            is_hol = curr_d in holiday_dates

            if is_hol:
                p_in = None
                p_out = None
                status = f"Holiday ({holiday_dates[curr_d]})"
                net_hours = 0.0
            elif is_sun:
                p_in = None
                p_out = None
                status = "Sunday"
                net_hours = 0.0
            else:
                p_in = datetime(2026, 8, day, 9, 0, 0)
                p_out = datetime(2026, 8, day, 17, 30, 0)
                status = "Present"
                net_hours = 8.0

            att = Attendance(
                worker_id=uid,
                date=curr_d,
                status=status,
                punch_in=p_in,
                punch_out=p_out,
                net_working_hours=net_hours,
                late_minutes=0,
                ot_hours=0.0,
                is_sunday=is_sun
            )
            db.add(att)
            created_records.append(att)

        db.commit()
        print(f"Created {len(created_records)} attendance records for August 2026.")

        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == uid).first()
        if not profile:
            profile = SalaryProfile(worker_id=uid, monthly_salary=20000.0)
            db.add(profile)
            db.commit()

        PayrollSyncEngine.sync_daily_attendance(db, created_records[-1], profile)

        payroll = db.query(PayrollRecord).filter(PayrollRecord.worker_id == uid, PayrollRecord.month == "2026-08").first()
        if payroll:
            print(f"August Payroll Updated for {worker.name}:")
            print(f"  - Days Present: {payroll.days_present}")
            print(f"  - Days Absent: {payroll.days_absent}")
            print(f"  - Paid Days: {payroll.net_working_days}")
            print(f"  - Base Monthly Salary: INR {payroll.base_salary}")
            print(f"  - Final Salary: INR {payroll.final_salary}\n")

finally:
    db.close()
