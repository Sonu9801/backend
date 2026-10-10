import sys
from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll
from app.models.payroll import AdvanceRequest, PayrollRecord
from app.models.user import User
from collections import defaultdict

def main():
    db = SessionLocal()
    results = get_employee_payroll(month='2026-09', db=db)
    print(f"Total employees in Payroll (2026-09): {len(results)}\n")

    advances = db.query(AdvanceRequest).all()
    adv_by_worker = defaultdict(list)
    for a in advances:
        adv_by_worker[a.worker_id].append((a.id, a.amount, a.status, a.reason))

    print("=" * 115)
    print(f"{'EMP ID':<12} | {'NAME':<24} | {'DEPT':<16} | {'P':<4} {'A':<4} | {'BASE':<7} | {'GROSS':<9} | {'DED':<8} | {'FINAL':<9} | STATUS")
    print("=" * 115)

    discrepancies = []
    advance_workers = []

    for r in results:
        wid = r['id']
        name = r['employeeName']
        empid = r['employeeId']
        dept = r['department'] or 'General'
        pres = r['presentDays']
        abs_d = r['absentDays']
        base = r['baseSalary']
        ot_amt = r['otAmount']
        sun_amt = r['sundayAmount']
        gross = r['totalSalary']
        ded = r['deductions']
        final = r['finalSalary']
        status = r['status']

        expected_final = round(gross - ded, 2)
        if abs(final - expected_final) > 0.05:
            discrepancies.append((name, empid, final, expected_final))

        if ded > 0:
            advance_workers.append((name, empid, ded, gross, final))

        adv_mark = f" [DED: Rs.{ded:,.0f}]" if ded > 0 else ""
        print(f"{empid:<12} | {name:<24} | {dept:<16} | {pres:<4.1f} {abs_d:<4.1f} | Rs.{base:<5.0f} | Rs.{gross:<7.2f} | Rs.{ded:<6.2f} | Rs.{final:<7.2f} | {status}{adv_mark}")

    print("=" * 115)
    print(f"\n[SUMMARY OF ADVANCE DEDUCTIONS]: Total {len(advance_workers)} employees have Advance Deductions:")
    for w in advance_workers:
        print(f" - {w[0]} ({w[1]}): Gross Rs.{w[3]:,.2f} - Deduction Rs.{w[2]:,.2f} = Net Pay Rs.{w[4]:,.2f}")

    print(f"\n[MATH AUDIT CHECK]: Discrepancies between (Gross - Deductions) and Final Salary: {len(discrepancies)}")
    for d in discrepancies:
        print("  WARNING:", d)

if __name__ == '__main__':
    main()
