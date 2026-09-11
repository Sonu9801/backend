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
    worker = db.query(User).filter(User.id == 31).first()
    if not worker:
        print("Worker 31 not found!")
    else:
        # Update user shift profile
        worker.shift_type = "Evening Shift (05:30 PM - 11:00 PM)"
        worker.shift_start = "17:30"
        worker.shift_end = "23:00"
        db.commit()
        db.refresh(worker)
        print(f"Updated User profile shift: {worker.shift_type} ({worker.shift_start} - {worker.shift_end})")

        holidays_db = db.query(Holiday).filter(
            Holiday.date >= date(2026, 8, 1),
            Holiday.date <= date(2026, 8, 31)
        ).all()
        holiday_dates = {h.date: h.name for h in holidays_db}

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

        # Clear existing August attendance for worker 31
        db.query(Attendance).filter(
            Attendance.worker_id == 31,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).delete()
        db.commit()

        created_records = []
        for day in range(1, 32):
            curr_d = date(2026, 8, day)
            is_sun = curr_d.weekday() == 6
            is_hol = curr_d in holiday_dates
            is_present = curr_d in present_dates

            if is_present:
                p_in = datetime(2026, 8, day, 17, 30, 0)
                p_out = datetime(2026, 8, day, 23, 0, 0)
                status = "Present"
                net_hours = 5.5
            elif is_hol:
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
                p_in = None
                p_out = None
                status = "Absent"
                net_hours = 0.0

            att = Attendance(
                worker_id=31,
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
        print(f"Created {len(created_records)} attendance records for Evening Shift.")

        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == 31).first()
        if not profile:
            profile = SalaryProfile(worker_id=31, monthly_salary=10000.0)
            db.add(profile)
            db.commit()

        PayrollSyncEngine.sync_daily_attendance(db, created_records[-1], profile)

        payroll = db.query(PayrollRecord).filter(PayrollRecord.worker_id == 31, PayrollRecord.month == "2026-08").first()
        if payroll:
            print(f"\nAugust Payroll Synced:")
            print(f"- Net Working Days: {payroll.net_working_days}")
            print(f"- Final Salary: INR {payroll.final_salary}")

finally:
    db.close()
