import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.routers.payroll import get_employee_payroll

db = SessionLocal()

for month in ['2026-08', '2026-09']:
    records = get_employee_payroll(month, db)
    print(f"Successfully recalculated payroll for {month} ({len(records)} active workers) under 30-day / 8-hour rule!\n")

db.close()
