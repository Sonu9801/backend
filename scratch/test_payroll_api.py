from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

try:
    res = get_employee_payroll(month="2026-08", db=db)
    sonus = [r for r in res if "Sonu" in r.get("employeeName", "")]
    print(f"Total employees returned in payroll table for August 2026: {len(res)}")
    print("Sonu records in payroll API response:")
    for s in sonus:
        print(s)

finally:
    db.close()
