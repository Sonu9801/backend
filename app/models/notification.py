from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, default="info") # error, warning, success, info
    title = Column(String, index=True)
    message = Column(String)
    module = Column(String) # e.g., production, attendance, invoices
    reference_id = Column(String, nullable=True) # e.g., tracking ID or worker ID
    target_url = Column(String, nullable=True) # e.g., /production?tab=incoming&vehicleId=FF-1234
    
    assigned_role = Column(String, nullable=True) # e.g., owner, manager, supervisor
    assigned_user_id = Column(Integer, nullable=True)
    
    read = Column(Boolean, default=False)
    clicked = Column(Boolean, default=False)
    archived = Column(Boolean, default=False)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
