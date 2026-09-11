from app.database import SessionLocal
from app.models.payroll import PayrollRecord, AdvanceRequest

db = SessionLocal()

try:
    for uid in [32, 5]:
        pr = db.query(PayrollRecord).filter(PayrollRecord.worker_id == uid, PayrollRecord.month == "2026-08").first()
        advs = db.query(AdvanceRequest).filter(AdvanceRequest.worker_id == uid).all()
        print(f"Worker ID {uid}:")
        if pr:
            print(f"  Base Salary: {pr.base_salary}")
            print(f"  Days Present: {pr.days_present}")
            print(f"  Days Absent: {pr.days_absent}")
            print(f"  Net Paid Days: {pr.net_working_days}")
            print(f"  OT Amount: {pr.ot_amount}")
            print(f"  Sunday Amount: {pr.sunday_amount}")
            print(f"  Bonus Amount: {pr.bonus_amount}")
            print(f"  Deductions: {pr.deductions}")
            print(f"  Final Salary: {pr.final_salary}")
        print(f"  Advances ({len(advs)}): {[(a.amount, a.status, a.deducted_in_payroll) for a in advs]}\n")

finally:
    db.close()
