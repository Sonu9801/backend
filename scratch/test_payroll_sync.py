import sys, os
sys.path.append(os.path.abspath("."))
from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

def test():
    db = SessionLocal()
    data = get_employee_payroll(month="2026-08", db=db)
    emp19 = [d for d in data if d.get("employeeId") == "FOX-EMP-019"]
    print("FOX-EMP-019 Payroll Data:")
    for d in emp19:
        print(f"Name: {d['employeeName']}, Base Salary: {d['baseSalary']}, Gross: {d['totalSalary']}, Final Net: {d['finalSalary']}, Status: {d['status']}")

if __name__ == "__main__":
    test()
