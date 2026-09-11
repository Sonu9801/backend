from app.database import SessionLocal
from app.models.user import User
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord
from app.models.attendance import Attendance
from datetime import date

db = SessionLocal()

try:
    for uid in [1, 5, 32]:
        u = db.query(User).filter(User.id == uid).first()
        sp = db.query(SalaryProfile).filter(SalaryProfile.worker_id == uid).first()
        pr = db.query(PayrollRecord).filter(PayrollRecord.worker_id == uid, PayrollRecord.month == "2026-08").first()
        att_count = db.query(Attendance).filter(
            Attendance.worker_id == uid,
            Attendance.date >= date(2026, 8, 1),
            Attendance.date <= date(2026, 8, 31)
        ).count()

        print(f"User ID {uid}: Name='{u.name}', EmpID='{u.employee_id}', Role='{u.role}'")
        print(f"  Salary Profile: {sp.monthly_salary if sp else 'None'}")
        print(f"  August Payroll: {pr.final_salary if pr else 'None'} (Present: {pr.days_present if pr else 'None'})")
        print(f"  August Attendance Records Count: {att_count}\n")

finally:
    db.close()
