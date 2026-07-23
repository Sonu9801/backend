from app.database import SessionLocal
from app.models.attendance import Attendance
from datetime import datetime, timedelta
import random

def update_times():
    db = SessionLocal()
    records = db.query(Attendance).all()
    print(f"Updating {len(records)} records...")
    
    for r in records:
        if not r.punch_in and r.status in ["Present", "Half Day"]:
            # Randomize punch in around 9 AM
            base_time = datetime.combine(r.date, datetime.min.time())
            punch_in = base_time + timedelta(hours=9, minutes=random.randint(-15, 15))
            r.punch_in = punch_in
            
            if r.status == "Present":
                # Randomize punch out around 6 PM + OT
                punch_out = punch_in + timedelta(hours=9 + (r.ot_hours or 0))
            else:
                # Half day punch out around 1 PM
                punch_out = punch_in + timedelta(hours=4)
                
            r.punch_out = punch_out
            
    db.commit()
    print("Successfully updated punch in/out times.")

if __name__ == "__main__":
    update_times()
