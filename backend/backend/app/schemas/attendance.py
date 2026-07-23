from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class AttendanceBase(BaseModel):
    worker_id: int
    date: date
    status: str
    net_working_hours: float
    break_time: float
    late_minutes: int
    early_exit_minutes: int
    ot_hours: float
    is_sunday: bool

class AttendanceResponse(AttendanceBase):
    id: int
    punch_in: Optional[datetime] = None
    punch_out: Optional[datetime] = None
    punch_in_photo_url: Optional[str] = None
    punch_out_photo_url: Optional[str] = None

    class Config:
        from_attributes = True

class ExceptionBase(BaseModel):
    worker_id: int
    date: date
    exception_type: str
    notes: Optional[str] = None

class ExceptionCreate(ExceptionBase):
    attendance_id: Optional[int] = None

class ExceptionResponse(ExceptionBase):
    id: int
    status: str
    approved_by_id: Optional[int] = None
    override_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
