from sqlalchemy import Column, Integer, String, Float, Boolean
from app.database import Base

class AttendanceSettings(Base):
    __tablename__ = 'attendance_settings'

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, default='Fox Enterprises')
    address = Column(String, default='239 Gurukul Industrial Area\nSector 39\nFaridabad\nHaryana 121010')
    latitude = Column(Float, default=28.3842)
    longitude = Column(Float, default=77.3090)
    geofence_radius = Column(Integer, default=200)

    default_shift_start = Column(String, default='09:30:00')
    default_shift_end = Column(String, default='18:00:00')
    present_window_end = Column(String, default='10:30:00')
    half_day_start = Column(String, default='13:30:00')

    enable_ot = Column(Boolean, default=True)
    ot_start_time = Column(String, default='18:30:00')
    ot_rate_multiplier = Column(Float, default=1.5)
    min_ot_minutes = Column(Integer, default=30)
    max_ot_hours = Column(Integer, default=4)

    enable_sunday_tracking = Column(Boolean, default=True)
    sunday_rate_multiplier = Column(Float, default=2.0)
    sunday_ot_rate = Column(Float, default=2.0)

    enable_face_verification = Column(Boolean, default=True)
    required_images = Column(Integer, default=5)
    min_match_percent = Column(Integer, default=85)
    retention_days = Column(Integer, default=30)

    single_device_mode = Column(Boolean, default=True)
    allow_device_change = Column(Boolean, default=False)
    require_supervisor_approval = Column(Boolean, default=True)

    attendance_reminder = Column(Boolean, default=True)
    punch_out_reminder = Column(Boolean, default=True)
    missing_punch_alert = Column(Boolean, default=True)
    leave_alerts = Column(Boolean, default=True)
