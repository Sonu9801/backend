import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()
records = get_employee_payroll('2026-08', db)
print(f"Successfully recalculated payroll for {len(records)} active workers under 30-day / 7-hour rule!\n")
print(f"{'EMP ID':<12} {'Employee Name':<20} {'Dept':<12} {'Base Salary':<14} {'OT Pay':<12} {'Sunday Pay':<14} {'Final Salary':<14}")
print("-" * 98)

for r in records:
    print(f"{r['employeeId']:<12} {r['employeeName']:<20} {(r['department'] or 'Unassigned'):<12} Rs. {r['baseSalary']:<10} Rs. {r['otAmount']:<8} Rs. {r['sundayAmount']:<10} Rs. {r['finalSalary']:<10}")

db.close()
