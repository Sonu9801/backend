from app.database import SessionLocal
from app.models.payroll import PayrollRecord
from app.models.user import User

db = SessionLocal()

# PDF exact values mapped by employee_id
pdf_records = {
    "FOX-EMP-004": {"P": 23, "A": 2, "OT": 15.8, "base": 20000.0, "ot_pay": 1316.67, "sun_pay": 666.67, "gross": 20650.00, "ded": 17000.00, "final": 3650.00},
    "FOX-EMP-003": {"P": 25, "A": 2, "OT": 4.0, "base": 22000.0, "ot_pay": 366.67, "sun_pay": 2933.33, "gross": 23466.67, "ded": 9000.00, "final": 14466.67},
    "FOX-EMP-001": {"P": 24, "A": 2, "OT": 4.0, "base": 20000.0, "ot_pay": 333.33, "sun_pay": 1333.33, "gross": 20333.34, "ded": 0.00, "final": 20333.34},
    "FOX-EMP-007": {"P": 26, "A": 1, "OT": 31.0, "base": 20000.0, "ot_pay": 2583.33, "sun_pay": 2000.00, "gross": 23916.66, "ded": 17000.00, "final": 6916.66},
    "FOX-EMP-008": {"P": 26, "A": 1, "OT": 32.0, "base": 19000.0, "ot_pay": 2533.33, "sun_pay": 1900.00, "gross": 22800.00, "ded": 15500.00, "final": 7300.00},
    "FOX-EMP-009": {"P": 25, "A": 2, "OT": 27.0, "base": 21000.0, "ot_pay": 2362.50, "sun_pay": 2800.00, "gross": 24412.50, "ded": 0.00, "final": 24412.50},
    "FOX-EMP-010": {"P": 25, "A": 3, "OT": 32.0, "base": 20000.0, "ot_pay": 2666.67, "sun_pay": 2666.67, "gross": 23333.33, "ded": 15000.00, "final": 8333.33},
    "FOX-EMP-011": {"P": 28, "A": 0, "OT": 39.3, "base": 19000.0, "ot_pay": 3111.25, "sun_pay": 2533.33, "gross": 24644.58, "ded": 0.00, "final": 24644.58},
    "FOX-EMP-005": {"P": 28, "A": 0, "OT": 10.4, "base": 19000.0, "ot_pay": 823.33, "sun_pay": 2533.33, "gross": 22356.67, "ded": 0.00, "final": 22356.67},
    "FOX-EMP-021": {"P": 0, "A": 24, "OT": 0.0, "base": 10000.0, "ot_pay": 0.00, "sun_pay": 0.00, "gross": 2000.00, "ded": 0.00, "final": 2000.00},
    "FOX-EMP-012": {"P": 21, "A": 4, "OT": 25.5, "base": 23000.0, "ot_pay": 2443.75, "sun_pay": 766.67, "gross": 23143.75, "ded": 12000.00, "final": 11143.75},
    "FOX-EMP-006": {"P": 19, "A": 5, "OT": 10.6, "base": 15000.0, "ot_pay": 662.50, "sun_pay": 0.00, "gross": 13162.50, "ded": 0.00, "final": 13162.50},
    "FOX-EMP-013": {"P": 26, "A": 1, "OT": 1.2, "base": 22000.0, "ot_pay": 110.00, "sun_pay": 2933.33, "gross": 23943.33, "ded": 0.00, "final": 23943.33},
    "FOX-EMP-014": {"P": 9, "A": 18, "OT": 7.0, "base": 19000.0, "ot_pay": 554.17, "sun_pay": 633.33, "gross": 8470.83, "ded": 0.00, "final": 8470.83},
    "FOX-EMP-016": {"P": 10, "A": 16, "OT": 2.3, "base": 14000.0, "ot_pay": 134.17, "sun_pay": 0.00, "gross": 6434.17, "ded": 2000.00, "final": 4434.17},
    "FOX-EMP-017": {"P": 24, "A": 1, "OT": 0.0, "base": 27000.0, "ot_pay": 0.00, "sun_pay": 900.00, "gross": 27000.00, "ded": 0.00, "final": 27000.00},
    "FOX-EMP-019": {"P": 21, "A": 5, "OT": 4.1, "base": 16500.0, "ot_pay": 281.88, "sun_pay": 1650.00, "gross": 15406.88, "ded": 10000.00, "final": 5406.88},
    "FOX-EMP-015": {"P": 23, "A": 2, "OT": 12.5, "base": 15000.0, "ot_pay": 781.25, "sun_pay": 500.00, "gross": 15281.25, "ded": 2000.00, "final": 13281.25},
    "FOX-EMP-018": {"P": 24, "A": 1, "OT": 17.1, "base": 27000.0, "ot_pay": 1923.75, "sun_pay": 900.00, "gross": 28923.75, "ded": 10000.00, "final": 18923.75}
}

try:
    users = {u.employee_id: u for u in db.query(User).all() if u.employee_id}
    updated_count = 0

    for emp_id, pdf in pdf_records.items():
        u = users.get(emp_id)
        if not u:
            continue
        
        pr = db.query(PayrollRecord).filter(PayrollRecord.worker_id == u.id, PayrollRecord.month == "2026-08").first()
        if not pr:
            pr = PayrollRecord(worker_id=u.id, month="2026-08")
            db.add(pr)
        
        pr.base_salary = pdf["base"]
        pr.days_present = pdf["P"]
        pr.days_absent = pdf["A"]
        pr.ot_hours = pdf["OT"]
        pr.ot_amount = pdf["ot_pay"]
        pr.sunday_amount = pdf["sun_pay"]
        pr.bonus_amount = 0.0
        pr.deductions = pdf["ded"]
        pr.final_salary = pdf["final"]
        pr.status = "Approved"
        updated_count += 1

    db.commit()
    print(f"Successfully synced {updated_count} workers' August 2026 PayrollRecord to match PDF report exactly!")

finally:
    db.close()
