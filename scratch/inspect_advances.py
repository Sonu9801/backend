from app.database import SessionLocal
from app.models.payroll import AdvanceRequest, PayrollRecord

db = SessionLocal()

try:
    advances = db.query(AdvanceRequest).all()
    print(f"Total Advance Requests in DB: {len(advances)}")
    for a in advances:
        print(f"ID: {a.id}, WorkerID: {a.worker_id}, Amount: {a.amount}, Reason: {a.reason}, Status: {a.status}, DeductedInPayroll: {a.deducted_in_payroll}")

    print("\nPayroll Records with Deductions > 0:")
    records = db.query(PayrollRecord).filter(PayrollRecord.deductions > 0).all()
    print(f"Found {len(records)} payroll records with deductions:")
    for r in records:
        print(f"WorkerID: {r.worker_id}, Month: {r.month}, Deductions: {r.deductions}, Base: {r.base_salary}, Final: {r.final_salary}")

finally:
    db.close()
