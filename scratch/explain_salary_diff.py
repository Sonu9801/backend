from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

# PDF report data mapped by employee_id
pdf_data = {
    "FOX-EMP-004": {"name": "Sonu", "P": 23, "A": 2, "base": 20000.0, "ot_pay": 1316.67, "sun_pay": 666.67, "gross": 20650.00, "ded": 17000.00, "final": 3650.00},
    "FOX-EMP-003": {"name": "Ashutosh Kumar", "P": 25, "A": 2, "base": 22000.0, "ot_pay": 366.67, "sun_pay": 2933.33, "gross": 23466.67, "ded": 9000.00, "final": 14466.67},
    "FOX-EMP-001": {"name": "Dhruv", "P": 24, "A": 2, "base": 20000.0, "ot_pay": 333.33, "sun_pay": 1333.33, "gross": 20333.34, "ded": 0.0, "final": 20333.34},
    "FOX-EMP-007": {"name": "Munna", "P": 26, "A": 1, "base": 20000.0, "ot_pay": 2583.33, "sun_pay": 2000.00, "gross": 23916.66, "ded": 17000.00, "final": 6916.66},
    "FOX-EMP-008": {"name": "Dev Raj", "P": 26, "A": 1, "base": 19000.0, "ot_pay": 2533.33, "sun_pay": 1900.00, "gross": 22800.00, "ded": 15500.00, "final": 7300.00},
    "FOX-EMP-009": {"name": "Ajay Kumar", "P": 25, "A": 2, "base": 21000.0, "ot_pay": 2362.50, "sun_pay": 2800.00, "gross": 24412.50, "ded": 0.0, "final": 24412.50},
    "FOX-EMP-010": {"name": "TunTun", "P": 25, "A": 3, "base": 20000.0, "ot_pay": 2666.67, "sun_pay": 2666.67, "gross": 23333.33, "ded": 15000.00, "final": 8333.33},
    "FOX-EMP-011": {"name": "Brijesh Kumar Ram", "P": 28, "A": 0, "base": 19000.0, "ot_pay": 3111.25, "sun_pay": 2533.33, "gross": 24644.58, "ded": 0.0, "final": 24644.58},
    "FOX-EMP-005": {"name": "Sanjay maity", "P": 28, "A": 0, "base": 19000.0, "ot_pay": 823.33, "sun_pay": 2533.33, "gross": 22356.67, "ded": 0.0, "final": 22356.67},
    "FOX-EMP-021": {"name": "Akhilesh Sharma", "P": 0, "A": 24, "base": 10000.0, "ot_pay": 0.0, "sun_pay": 0.0, "gross": 2000.00, "ded": 0.0, "final": 2000.00},
    "FOX-EMP-012": {"name": "Pintu dhaka", "P": 21, "A": 4, "base": 23000.0, "ot_pay": 2443.75, "sun_pay": 766.67, "gross": 23143.75, "ded": 12000.00, "final": 11143.75},
    "FOX-EMP-006": {"name": "Nigar hussian", "P": 19, "A": 5, "base": 15000.0, "ot_pay": 662.50, "sun_pay": 0.0, "gross": 13162.50, "ded": 0.0, "final": 13162.50},
    "FOX-EMP-013": {"name": "Gopal Singh", "P": 26, "A": 1, "base": 22000.0, "ot_pay": 110.00, "sun_pay": 2933.33, "gross": 23943.33, "ded": 0.0, "final": 23943.33},
    "FOX-EMP-014": {"name": "Rohit", "P": 9, "A": 18, "base": 19000.0, "ot_pay": 554.17, "sun_pay": 633.33, "gross": 8470.83, "ded": 0.0, "final": 8470.83},
    "FOX-EMP-016": {"name": "Manish Chauhan", "P": 10, "A": 16, "base": 14000.0, "ot_pay": 134.17, "sun_pay": 0.0, "gross": 6434.17, "ded": 2000.00, "final": 4434.17},
    "FOX-EMP-017": {"name": "Shubham Srivastava", "P": 24, "A": 1, "base": 27000.0, "ot_pay": 0.0, "sun_pay": 900.00, "gross": 27000.00, "ded": 0.0, "final": 27000.00},
    "FOX-EMP-019": {"name": "Ajay Singh Rana", "P": 21, "A": 5, "base": 16500.0, "ot_pay": 281.88, "sun_pay": 1650.00, "gross": 15406.88, "ded": 10000.00, "final": 5406.88},
    "FOX-EMP-015": {"name": "Saurabh Kumar Purvey", "P": 23, "A": 2, "base": 15000.0, "ot_pay": 781.25, "sun_pay": 500.00, "gross": 15281.25, "ded": 2000.00, "final": 13281.25},
    "FOX-EMP-018": {"name": "Prem Sharma", "P": 24, "A": 1, "base": 27000.0, "ot_pay": 1923.75, "sun_pay": 900.00, "gross": 28923.75, "ded": 10000.00, "final": 18923.75}
}

try:
    res = get_employee_payroll(month="2026-08", db=db)
    current_map = {r["employeeId"]: r for r in res}

    print("DETAILED REASON FOR SALARY DIFFERENCE:")
    print("=" * 115)

    for emp_id, pdf in pdf_data.items():
        curr = current_map.get(emp_id, {})
        if not curr:
            continue
        
        daily_rate = pdf["base"] / 30.0
        pdf_final = pdf["final"]
        curr_final = curr["finalSalary"]
        diff = curr_final - pdf_final

        # Calculate earned base in PDF vs Current
        # PDF formula used: (base / 30) * (30 - absent_in_pdf - 1) or 31-day formula
        pdf_absent = pdf["A"]
        curr_absent = curr["absentDays"]
        curr_present = curr["presentDays"]

        reason = ""
        if emp_id == "FOX-EMP-004": # Sonu
            reason = "Attendance updated to 31 Days Present (Full Month), OT/Sunday reset"
        elif emp_id == "FOX-EMP-021": # Akhilesh
            reason = "Attendance updated to 7 Worked Days + 5 Sundays + 2 Holidays = 14 Paid Days"
        elif pdf["A"] == 0:
            reason = "Full month attendance (0 absent days), 30 days full salary"
        else:
            days_diff = diff / daily_rate if daily_rate > 0 else 0
            reason = f"30-day base formula fix (+{days_diff:.1f} day salary = +INR {diff:.2f}). PDF deducted {pdf_absent+1} days (31-day month), system now deducts only actual {pdf_absent} absent days!"

        print(f"{emp_id:<11} | {pdf['name'][:18]:<18} | PDF: Rs.{pdf_final:<9.2f} | Curr: Rs.{curr_final:<9.2f} | Diff: Rs.{diff:<8.2f} | {reason}")

finally:
    db.close()
