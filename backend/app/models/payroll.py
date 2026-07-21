from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class AdvanceRequest(Base):
    __tablename__ = "advance_requests"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    request_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)
    status = Column(String, default="Pending") # Pending, Approved, Rejected
    deducted_in_payroll = Column(Boolean, default=False)
    
    worker = relationship("User", foreign_keys=[worker_id])

class PayrollRecord(Base):
    __tablename__ = "payroll_records"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    month = Column(String, nullable=False) # e.g. "2026-06"
    status = Column(String, default="Draft") # Draft, Approved, Paid
    
    base_salary = Column(Float, default=0.0)
    
    days_present = Column(Integer, default=0)
    days_absent = Column(Integer, default=0)
    half_days = Column(Integer, default=0)
    late_count = Column(Integer, default=0)
    working_hours = Column(Float, default=0.0)
    ot_hours = Column(Float, default=0.0)
    sunday_work = Column(Integer, default=0)
    holiday_work = Column(Integer, default=0)
    leave_days = Column(Integer, default=0)
    net_working_days = Column(Float, default=0.0)
    
    ot_amount = Column(Float, default=0.0)
    sunday_amount = Column(Float, default=0.0)
    bonus_amount = Column(Float, default=0.0)
    deductions = Column(Float, default=0.0)
    final_salary = Column(Float, default=0.0)
    
    worker = relationship("User", foreign_keys=[worker_id])
