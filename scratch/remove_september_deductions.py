from app.database import SessionLocal
from app.models.payroll import AdvanceRequest, PayrollRecord

db = SessionLocal()

try:
    # 1. Delete all the advance requests
    advances = db.query(AdvanceRequest).all()
    deleted_count = len(advances)
    db.query(AdvanceRequest).delete()
    db.commit()
    print(f"Deleted {deleted_count} AdvanceRequest records!")

    # 2. Clear deductions on all PayrollRecords and recalculate final_salary
    payroll_records = db.query(PayrollRecord).all()
    updated_records = 0
    for pr in payroll_records:
        if (pr.deductions or 0) > 0:
            pr.deductions = 0.0
            total_salary = (pr.earned_base_salary if hasattr(pr, 'earned_base_salary') and pr.earned_base_salary is not None else 0.0) or 0.0
            # Recalculate final_salary: base + ot + sunday + bonus - deductions
            base = pr.base_salary or 0.0
            ot = pr.ot_amount or 0.0
            sun = pr.sunday_amount or 0.0
            bonus = pr.bonus_amount or 0.0
            
            # Using earned base salary if available, else calculate from net_working_days
            days_p = pr.net_working_days or pr.days_present or 0.0
            earned_base = round((base / 30.0) * min(30.0, days_p), 2)
            
            pr.final_salary = round(earned_base + ot + sun + bonus, 2)
            updated_records += 1

    db.commit()
    print(f"Updated {updated_records} PayrollRecords by removing deductions!")

    # 3. Verify zero advance requests and zero deductions
    rem_advances = db.query(AdvanceRequest).count()
    rem_deductions = db.query(PayrollRecord).filter(PayrollRecord.deductions > 0).count()
    print(f"Remaining Advance Requests: {rem_advances}")
    print(f"Remaining Payroll Records with Deductions: {rem_deductions}")

finally:
    db.close()
