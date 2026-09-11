from app.database import SessionLocal
from app.models.user import User
from app.models.salary_profile import SalaryProfile
from app.models.payroll import PayrollRecord

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    profile = db.query(SalaryProfile).filter(SalaryProfile.worker_id == 31).first()
    payroll = db.query(PayrollRecord).filter(PayrollRecord.worker_id == 31, PayrollRecord.month == "2026-08").first()

    print(f"Worker: {worker.name} (ID: {worker.id})")
    if profile:
        print(f"Salary Profile: Monthly Salary = {profile.monthly_salary}, Daily Rate = {profile.monthly_salary / 30.0 if profile.monthly_salary else 0}")
    else:
        print("Salary Profile: None")

    if payroll:
        print(f"August Payroll Record: Days Present={payroll.days_present}, Days Absent={payroll.days_absent}, Base Salary={payroll.base_salary}, Final Salary={payroll.final_salary}")
    else:
        print("August Payroll Record: None")
finally:
    db.close()
