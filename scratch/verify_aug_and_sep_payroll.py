from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

try:
    res_aug = get_employee_payroll(month="2026-08", db=db)
    print("AUGUST 2026 PAYROLL SAMPLE (With Deductions):")
    print(f"{'EMP ID':<12} | {'Name':<22} | {'Base Salary':<12} | {'Deductions':<12} | {'Final Salary':<12}")
    print("-" * 75)
    for r in res_aug:
        if r['deductions'] > 0:
            print(f"{r['employeeId']:<12} | {r['employeeName'].strip():<22} | INR {r['baseSalary']:<8.2f} | INR {r['deductions']:<8.2f} | INR {r['finalSalary']:<8.2f}")

    res_sep = get_employee_payroll(month="2026-09", db=db)
    print("\nSEPTEMBER 2026 PAYROLL SAMPLE (Zero Deductions):")
    print(f"{'EMP ID':<12} | {'Name':<22} | {'Base Salary':<12} | {'Deductions':<12} | {'Final Salary':<12}")
    print("-" * 75)
    for r in res_sep[:5]:
        print(f"{r['employeeId']:<12} | {r['employeeName'].strip():<22} | INR {r['baseSalary']:<8.2f} | INR {r['deductions']:<8.2f} | INR {r['finalSalary']:<8.2f}")

finally:
    db.close()
