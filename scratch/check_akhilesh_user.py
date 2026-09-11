from app.database import SessionLocal
from app.models.user import User

db = SessionLocal()

try:
    worker = db.query(User).filter(User.id == 31).first()
    print(f"Worker ID: {worker.id}")
    print(f"Name: {worker.name}")
    print(f"Employee ID: {worker.employee_id}")
    print(f"Employment Status: {worker.employment_status}")
    print(f"Status: {worker.status}")
    print(f"Role: {worker.role}")

    # Also list all workers in db
    all_workers = db.query(User).all()
    print(f"\nTotal users in DB: {len(all_workers)}")
    for w in all_workers:
        print(f"ID: {w.id}, Name: '{w.name}', EmpID: {w.employee_id}, EmpStatus: {w.employment_status}")
finally:
    db.close()
