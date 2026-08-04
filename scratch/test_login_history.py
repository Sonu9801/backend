import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal
from app.models.user import User
from app.models.user_login_history import UserLoginHistory
from datetime import datetime

db = SessionLocal()
try:
    user = db.query(User).filter(User.email == "skhjp2000@gmail.com").first()
    if not user:
        print("Test user not found.")
    else:
        print(f"Found user: {user.name}")
        # Insert a mock live login
        hist = UserLoginHistory(
            user_id=user.id,
            device="Chrome on Windows (Live Test)",
            ip_address="127.0.0.1",
            location="Delhi, India",
            login_time=datetime.utcnow()
        )
        db.add(hist)
        db.commit()
        print("Recorded new live login entry.")
        
        # Query it back
        records = db.query(UserLoginHistory).filter(UserLoginHistory.user_id == user.id).all()
        print(f"Total login history records for this user: {len(records)}")
        for r in records:
            print(f"- {r.device} | {r.location} | {r.login_time}")
finally:
    db.close()
