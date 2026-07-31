from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class WorkerDailyPerformance(Base):
    __tablename__ = "worker_daily_performance"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    assigned_jobs = Column(Integer, default=0)
    completed_jobs = Column(Integer, default=0)
    running_jobs = Column(Integer, default=0)
    pending_jobs = Column(Integer, default=0)
    
    working_hours = Column(Float, default=0.0)
    break_time = Column(Float, default=0.0)
    overtime = Column(Float, default=0.0)
    efficiency = Column(Float, default=100.0)
    
    supervisor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(Text, nullable=True)
    approval_status = Column(String, default="Pending") # Pending, Approved, Rejected
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    worker = relationship("User", foreign_keys=[worker_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])


class TeamDailySummary(Base):
    __tablename__ = "team_daily_summary"

    id = Column(Integer, primary_key=True, index=True)
    supervisor_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    
    department = Column(String, nullable=True)
    total_workers = Column(Integer, default=0)
    present_workers = Column(Integer, default=0)
    jobs_completed = Column(Integer, default=0)
    average_efficiency = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supervisor = relationship("User", foreign_keys=[supervisor_id])
