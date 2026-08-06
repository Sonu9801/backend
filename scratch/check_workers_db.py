import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()
try:
    workers = db.query(User).filter(User.role == "worker").all()
    print(f"Total workers: {len(workers)}")
    for w in workers:
        print(f"ID: {w.id}, Name: {w.name}, Employee ID: {w.employee_id}, Status: {w.employment_status}")
finally:
    db.close()
