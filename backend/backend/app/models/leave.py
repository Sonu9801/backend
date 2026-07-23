from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    leave_type = Column(String, nullable=False) # Casual Leave, Sick Leave, Paid Leave, Unpaid Leave, Emergency Leave, Half Day Leave
    reason = Column(String, nullable=True)
    
    status = Column(String, default="Pending") # Pending, Approved, Rejected, Cancelled
    admin_remarks = Column(String, nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    worker = relationship("User", foreign_keys=[worker_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
