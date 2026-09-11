from app.database import SessionLocal
from app.models.user import User
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    users = db.query(User).filter(User.name.ilike("%sonu%")).all()
    print(f"Found {len(users)} users matching 'sonu':")
    for u in users:
        print(f"ID: {u.id}, Name: '{u.name}', Role: {u.role}, Employee ID: {u.employee_id}, Shift: {u.shift_type}")

    sonu = db.query(User).filter(User.name.ilike("%sonu kumar%")).first()
    if not sonu:
        sonu = users[0] if users else None

    if sonu:
        print(f"\nTarget Worker: {sonu.name} (ID: {sonu.id}, EmpID: {sonu.employee_id})")

        profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == sonu.id).first()
        if profile:
            print(f"Salary Profile: Monthly Salary = {profile.monthly_salary}, Daily Wage = {profile.daily_wage}, Salary Type = {profile.salary_type}")
        else:
            print("Salary Profile: None")

        payroll = db.query(PayrollRecord).filter(PayrollRecord.worker_id == sonu.id, PayrollRecord.month == "2026-08").first()
        if payroll:
            print(f"August Payroll: Present={payroll.days_present}, Absent={payroll.days_absent}, Base={payroll.base_salary}, Final={payroll.final_salary}")
        else:
            print("August Payroll: None")

        records = db.query(Attendance).filter(
            Attendance.worker_id == sonu.id,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).all()
        print(f"August Attendance Records Count: {len(records)}")

finally:
    db.close()
