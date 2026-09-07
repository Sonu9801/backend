import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.user import User
from app.models.attendance import Attendance
from app.models.holiday import Holiday
from datetime import date

db = SessionLocal()

w = db.query(User).filter(User.name.like('%Ashutosh%')).first()
print(f"Worker: {w.id} - {w.name}")

logs = db.query(Attendance).filter(
    Attendance.worker_id == w.id,
    Attendance.date >= '2026-08-01',
    Attendance.date <= '2026-08-31'
).order_by(Attendance.date).all()

print("\n--- ALL ASHUTOSH AUGUST ATTENDANCE LOGS ---")
tot_ot_hrs = 0.0
tot_sun_hrs = 0.0

holidays = {h.date for h in db.query(Holiday).filter(Holiday.date >= '2026-08-01', Holiday.date <= '2026-08-31').all()}

for l in logs:
    dt = l.date if not isinstance(l.date, str) else date.fromisoformat(str(l.date)[:10])
    is_sun = (dt.weekday() == 6)
    is_hol = (dt in holidays)
    ot = l.ot_hours or 0.0
    net_h = l.net_working_hours or 0.0
    in_t = l.punch_in.strftime('%H:%M') if l.punch_in else 'N/A'
    out_t = l.punch_out.strftime('%H:%M') if l.punch_out else 'N/A'
    
    print(f"Date: {dt} | Day: {dt.strftime('%A'):<9} | Status: {l.status:<12} | In: {in_t:<5} | Out: {out_t:<5} | Net Hrs: {net_h:<4} | OT Hrs: {ot}")
    
    tot_ot_hrs += ot
    if (is_sun or is_hol) and (l.status in ["present", "half day", "sunday work", "holiday work"] or net_h > 0):
        tot_sun_hrs += net_h

base_salary = 22000.0
last_day = 31
daily_rate = base_salary / last_day
hourly_rate = daily_rate / 8.0
sunday_hourly_rate = hourly_rate * 2.0

ot_amount = tot_ot_hrs * hourly_rate
sunday_amount = tot_sun_hrs * sunday_hourly_rate

print("\n--- STATS & CALCULATIONS ---")
print(f"Base Monthly Salary = INR {base_salary}")
print(f"Days in Month (August) = {last_day}")
print(f"Daily Rate = 22000 / 31 = INR {daily_rate:.4f}")
print(f"Hourly Rate = {daily_rate:.4f} / 8 = INR {hourly_rate:.4f}/hr")
print(f"Sunday 2x Hourly Rate = {hourly_rate:.4f} * 2 = INR {sunday_hourly_rate:.4f}/hr")
print(f"Total OT Hours = {tot_ot_hrs} hrs")
print(f"Calculated OT Amount = {tot_ot_hrs} * {hourly_rate:.4f} = INR {ot_amount:.2f}")
print(f"Total Sunday Worked Hours = {tot_sun_hrs} hrs")
print(f"Calculated Sunday Amount = {tot_sun_hrs} * {sunday_hourly_rate:.4f} = INR {sunday_amount:.2f}")

db.close()
