from app.schemas.base import CamelModel
from typing import Optional

class AttendanceSettingsBase(CamelModel):
    company_name: str
    address: str
    latitude: float
    longitude: float
    geofence_radius: int

    default_shift_start: str
    default_shift_end: str
    present_window_end: str
    half_day_start: str

    enable_ot: bool
    ot_start_time: str
    ot_rate_multiplier: float
    min_ot_minutes: int
    max_ot_hours: int

    enable_sunday_tracking: bool
    sunday_rate_multiplier: float
    sunday_ot_rate: float

    enable_face_verification: bool
    required_images: int
    min_match_percent: int
    retention_days: int

    single_device_mode: bool
    allow_device_change: bool
    require_supervisor_approval: bool

    attendance_reminder: bool
    punch_out_reminder: bool
    missing_punch_alert: bool
    leave_alerts: bool

class AttendanceSettingsCreate(AttendanceSettingsBase):
    pass

class AttendanceSettingsUpdate(AttendanceSettingsBase):
    pass

class AttendanceSettingsResponse(AttendanceSettingsBase):
    id: int

from datetime import date

class ShiftBase(CamelModel):
    name: str
    start_time: str
    end_time: str

class ShiftCreate(ShiftBase):
    pass

class ShiftUpdate(ShiftBase):
    pass

class ShiftResponse(ShiftBase):
    id: int

class HolidayBase(CamelModel):
    date: date
    name: str
    type: str

class HolidayCreate(HolidayBase):
    pass

class HolidayResponse(HolidayBase):
    id: int
