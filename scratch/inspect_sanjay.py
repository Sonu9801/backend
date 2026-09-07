import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.holiday import Holiday
from app.routers.payroll import get_employee_payroll
from datetime import date

db = SessionLocal()

workers = db.query(User).filter(User.name.like('%Sanjay%')).all()
print(f"Found {len(workers)} worker(s) named Sanjay:")
for w in workers:
    print(f"  ID: {w.id}, Name: '{w.name}', Emp ID: {w.employee_id}, Role: {w.role}, Dept: {w.department}")

w = workers[0] if workers else None
if w:
    logs = db.query(Attendance).filter(
        Attendance.worker_id == w.id,
        Attendance.date >= '2026-08-01',
        Attendance.date <= '2026-08-31'
    ).order_by(Attendance.date).all()

    print(f"\n--- ATTENDANCE LOGS FOR {w.name} (AUG 2026) ---")
    holidays = {h.date for h in db.query(Holiday).filter(Holiday.date >= '2026-08-01', Holiday.date <= '2026-08-31').all()}
    
    tot_present = 0.0
    tot_half = 0.0
    tot_absent = 0.0
    tot_sunday = 0.0
    tot_holiday = 0.0
    tot_ot = 0.0
    tot_sun_worked_hrs = 0.0

    for l in logs:
        dt = l.date if not isinstance(l.date, str) else date.fromisoformat(str(l.date)[:10])
        is_sun = (dt.weekday() == 6)
        is_hol = (dt in holidays)
        ot = l.ot_hours or 0.0
        net_h = l.net_working_hours or 0.0
        s = l.status or ''
        
        in_t = l.punch_in.strftime('%H:%M') if l.punch_in else 'N/A'
        out_t = l.punch_out.strftime('%H:%M') if l.punch_out else 'N/A'

        print(f"Date: {dt} | Day: {dt.strftime('%A'):<9} | Status: {s:<15} | In: {in_t:<5} | Out: {out_t:<5} | Net Hrs: {net_h:<4} | OT Hrs: {ot}")

        tot_ot += ot
        if (is_sun or is_hol) and (s.lower() in ["present", "half day", "sunday work", "holiday work"] or net_h > 0):
            tot_sun_worked_hrs += net_h
            if s.lower() == "half day": tot_half += 0.5
            else: tot_present += 1.0
        else:
            if s.lower() == "present": tot_present += 1.0
            elif s.lower() == "absent": tot_absent += 1.0
            elif s.lower() == "half day": tot_half += 1.0
            elif "leave" in s.lower(): pass
            elif "holiday" in s.lower(): tot_holiday += 1.0
            elif is_sun or s.lower() == "sunday": tot_sunday += 1.0

    payroll = get_employee_payroll('2026-08', db)
    p = next((rec for rec in payroll if rec['id'] == w.id), None)
    
    print("\n--- PAYROLL SUMMARY ---")
    if p:
        for k, val in p.items():
            print(f"  {k}: {val}")

db.close()
