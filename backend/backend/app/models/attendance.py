from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, nullable=False)
    punch_in = Column(DateTime)
    punch_out = Column(DateTime, nullable=True)
    status = Column(String)  # Present, Half Day, Absent, Sunday, Leave
    
    # New Fields for Enterprise Engine
    punch_in_photo_url = Column(String, nullable=True)
    punch_out_photo_url = Column(String, nullable=True)
    net_working_hours = Column(Float, default=0.0)
    break_time = Column(Float, default=0.0)
    late_minutes = Column(Integer, default=0)
    early_exit_minutes = Column(Integer, default=0)
    
    ot_hours = Column(Float, default=0.0)
    is_sunday = Column(Boolean, default=False)

    worker = relationship("User", back_populates="attendance_records", foreign_keys=[worker_id])
    exceptions = relationship("AttendanceException", back_populates="attendance", cascade="all, delete-orphan")

class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # Punch In, Punch Out
    latitude = Column(Float)
    longitude = Column(Float)
    
    # New Fields
    accuracy = Column(Float, nullable=True)
    address = Column(String, nullable=True)
    speed = Column(Float, nullable=True)
    network_type = Column(String, nullable=True)
    photo_url = Column(String, nullable=True)
    
    device_info = Column(String)
    ip_address = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_valid = Column(Boolean, default=True)

    worker = relationship("User", back_populates="attendance_logs")

class AttendanceException(Base):
    __tablename__ = "attendance_exceptions"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"))
    attendance_id = Column(Integer, ForeignKey("attendance.id"), nullable=True)
    date = Column(Date, nullable=False)
    
    exception_type = Column(String) # Forgot Punch Out, Outside Geofence, Manual Correction, etc.
    notes = Column(String, nullable=True)
    
    status = Column(String, default="Pending") # Pending, Approved, Rejected
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    override_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    worker = relationship("User", foreign_keys=[worker_id])
    attendance = relationship("Attendance", back_populates="exceptions")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    override_by = relationship("User", foreign_keys=[override_by_id])

