from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

try:
    res = get_employee_payroll(month="2026-08", db=db)
    print(f"Total employees returned: {len(res)}\n")
    print("Ordered list of employees:")
    for idx, r in enumerate(res, 1):
        print(f"{idx:2d}. {r['employeeId']} - {r['employeeName'].strip()} ({r['department']})")

finally:
    db.close()
