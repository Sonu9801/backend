from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.associations import vehicle_user_association, job_user_association

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default="operator")  # admin, operator, supervisor, viewer, worker, oem
    is_active = Column(Boolean, default=True)
    preferences = Column(JSON, nullable=True)
    dealer_name = Column(String, nullable=True)

    # OTP Authentication fields
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime, nullable=True)

    # Workforce/Worker Profile Fields (Nullable so admins/operators don't need them)
    employee_id = Column(String, unique=True, index=True, nullable=True)
    status = Column(String, default="Offline")  # Active, Break, Offline
    current_task_id = Column(String, nullable=True)
    hours_today = Column(Float, default=0.0)
    department = Column(String, nullable=True)
    performance_score = Column(Integer, default=100)

    mobile_number = Column(String, nullable=True)
    password = Column(String, default="1234")  # Fast PIN fallback for PWA kiosk login
    date_of_birth = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    designation = Column(String, nullable=True)
    joining_date = Column(String, nullable=True)
    employment_status = Column(String, default="Active")  # Active, Inactive, On Leave, Resigned
    
    profile_photo_url = Column(String, nullable=True)
    shift_type = Column(String, default="General Shift")
    shift_start = Column(String, default="09:30:00")
    shift_end = Column(String, default="18:00:00")
    
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_number = Column(String, nullable=True)
    emergency_contact_relationship = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    aadhaar_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    
    face_registration_status = Column(String, default="Pending")  # Pending, Completed

    # Relationships
    vehicles = relationship(
        "Vehicle",
        secondary=vehicle_user_association,
        back_populates="workers"
    )
    activities = relationship("ActivityEvent", back_populates="worker", cascade="all, delete-orphan")
    attendance_records = relationship("Attendance", back_populates="worker", cascade="all, delete-orphan", foreign_keys="Attendance.worker_id")
    attendance_logs = relationship("AttendanceLog", back_populates="worker", cascade="all, delete-orphan")
    salary_profile = relationship("SalaryProfile", back_populates="worker", uselist=False, cascade="all, delete-orphan")
    production_jobs = relationship(
        "ProductionJob",
        secondary=job_user_association,
        back_populates="workers"
    )
