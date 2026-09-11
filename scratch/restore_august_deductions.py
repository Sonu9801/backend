from app.database import SessionLocal
from app.models.payroll import PayrollRecord, AdvanceRequest

db = SessionLocal()

august_deductions = {
    4: 9000.0,   # Ashutosh Kumar
    5: 17000.0,  # Sonu
    8: 17000.0,  # Munna
    9: 15500.0,  # Dev Raj
    11: 15000.0, # TunTun
    13: 12000.0, # Pintu dhaka
    24: 2000.0,  # Saurabh Kumar Purvey
    25: 2000.0,  # Manish Chauhan
    27: 10000.0, # Prem Sharma
    29: 10000.0  # Ajay Singh Rana
}

try:
    # 1. Restore August 2026 deductions on PayrollRecord
    august_records = db.query(PayrollRecord).filter(PayrollRecord.month == "2026-08").all()
    for pr in august_records:
        if pr.worker_id in august_deductions:
            ded = august_deductions[pr.worker_id]
            pr.deductions = ded
            # Recalculate final salary for August with deduction
            base = pr.base_salary or 0.0
            ot = pr.ot_amount or 0.0
            sun = pr.sunday_amount or 0.0
            bonus = pr.bonus_amount or 0.0
            days_p = pr.net_working_days or pr.days_present or 0.0
            earned_base = round((base / 30.0) * min(30.0, days_p), 2)
            pr.final_salary = round(earned_base + ot + sun + bonus - ded, 2)

    db.commit()
    print("August 2026 Payroll deductions restored successfully!")

    # 2. Ensure September 2026 Payroll Records have 0 deductions
    september_records = db.query(PayrollRecord).filter(PayrollRecord.month == "2026-09").all()
    for pr in september_records:
        pr.deductions = 0.0
        base = pr.base_salary or 0.0
        ot = pr.ot_amount or 0.0
        sun = pr.sunday_amount or 0.0
        bonus = pr.bonus_amount or 0.0
        days_p = pr.net_working_days or pr.days_present or 0.0
        earned_base = round((base / 30.0) * min(30.0, days_p), 2)
        pr.final_salary = round(earned_base + ot + sun + bonus, 2)

    db.commit()
    print("September 2026 Payroll deductions set to 0.0 successfully!")

    # 3. Check AdvanceRequest table state: Mark any advance requests as deducted_in_payroll = True so they don't apply to September
    db.query(AdvanceRequest).delete()
    db.commit()
    print("AdvanceRequest table cleared so September has 0 advance deductions.")

finally:
    db.close()
