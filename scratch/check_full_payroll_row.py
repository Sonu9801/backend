from app.database import SessionLocal
from app.models.payroll import PayrollRecord

db = SessionLocal()

try:
    p = db.query(PayrollRecord).filter(PayrollRecord.worker_id == 31, PayrollRecord.month == "2026-08").first()
    if p:
        print(f"ID: {p.id}")
        print(f"Worker ID: {p.worker_id}")
        print(f"Month: {p.month}")
        print(f"Base Salary: {p.base_salary}")
        print(f"Days Present: {p.days_present}")
        print(f"Days Absent: {p.days_absent}")
        print(f"Half Days: {p.half_days}")
        print(f"Net Working Days: {p.net_working_days}")
        print(f"OT Hours: {p.ot_hours}")
        print(f"OT Amount: {p.ot_amount}")
        print(f"Sunday Amount: {p.sunday_amount}")
        print(f"Bonus: {p.bonus_amount}")
        print(f"Deductions: {p.deductions}")
        print(f"Final Salary: {p.final_salary}")
        print(f"Status: {p.status}")
    else:
        print("No PayrollRecord found for worker 31 in 2026-08")
finally:
    db.close()
