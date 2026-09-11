from datetime import date, timedelta
from app.database import SessionLocal
from app.models.holiday import Holiday

db = SessionLocal()

try:
    holidays_db = db.query(Holiday).filter(
        Holiday.date >= date(2026, 8, 1),
        Holiday.date <= date(2026, 8, 31)
    ).all()
    holiday_dates = {h.date: h.name for h in holidays_db}

    sundays = []
    holidays = []
    working_presents = [
        date(2026, 8, 1),
        date(2026, 8, 3),
        date(2026, 8, 4),
        date(2026, 8, 5),
        date(2026, 8, 6),
        date(2026, 8, 7),
        date(2026, 8, 8)
    ]

    print("August 2026 Calendar Breakdown:")
    for day in range(1, 32):
        curr_d = date(2026, 8, day)
        is_sun = curr_d.weekday() == 6
        is_hol = curr_d in holiday_dates

        if is_sun:
            sundays.append(curr_d)
        if is_hol:
            holidays.append((curr_d, holiday_dates[curr_d]))

        status = "Present (Worked)" if curr_d in working_presents else ("Sunday" if is_sun else ("Holiday" if is_hol else "Absent"))
        print(f"Date: {curr_d} ({curr_d.strftime('%a')}) -> {status}")

    print(f"\nSummary:")
    print(f"Worked Days (Present): {len(working_presents)}")
    print(f"Sundays Count ({len(sundays)}): {[s.strftime('%Y-%m-%d') for s in sundays]}")
    print(f"Holidays Count ({len(holidays)}): {[(h[0].strftime('%Y-%m-%d'), h[1]) for h in holidays]}")
    total_paid = len(working_presents) + len(sundays) + len(holidays)
    print(f"Total Paid Days = {len(working_presents)} present + {len(sundays)} sundays + {len(holidays)} holidays = {total_paid} days!")

finally:
    db.close()
