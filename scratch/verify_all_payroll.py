from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

try:
    res = get_employee_payroll(month="2026-08", db=db)
    print(f"Total Employees in Payroll for August 2026: {len(res)}\n")
    print(f"{'EMP ID':<12} | {'Name':<22} | {'Base Salary':<12} | {'Deductions':<12} | {'Final Salary':<12}")
    print("-" * 75)
    for r in res:
        print(f"{r['employeeId']:<12} | {r['employeeName'].strip():<22} | INR {r['baseSalary']:<8.2f} | INR {r['deductions']:<8.2f} | INR {r['finalSalary']:<8.2f}")

finally:
    db.close()
