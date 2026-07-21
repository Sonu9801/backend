from app.schemas.base import CamelModel
from typing import Optional, List

class WorkerBase(CamelModel):
    employee_id: str
    name: str
    status: str = "Offline"
    current_task_id: Optional[str] = None
    hours_today: float = 0.0
    department: str
    performance_score: int = 100
    mobile_number: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    designation: Optional[str] = None
    role: str = "Worker"
    joining_date: Optional[str] = None
    employment_status: str = "Active"
    
    profile_photo_url: Optional[str] = None
    shift_type: str = "General Shift"
    shift_start: str = "09:30:00"
    shift_end: str = "18:00:00"
    
    emergency_contact_name: Optional[str] = None
    emergency_contact_number: Optional[str] = None
    emergency_contact_relationship: Optional[str] = None
    address: Optional[str] = None
    
    aadhaar_number: Optional[str] = None
    pan_number: Optional[str] = None
    
    face_registration_status: str = "Pending"

class SalaryProfileBase(CamelModel):
    salary_type: str = "Monthly"
    monthly_salary: Optional[float] = None
    daily_wage: Optional[float] = None
    ot_rate_per_hour: float = 0.0
    sunday_rate_per_hour: float = 0.0

class WorkerCreate(WorkerBase):
    salary_profile: Optional[SalaryProfileBase] = None

class WorkerUpdate(WorkerBase):
    salary_profile: Optional[SalaryProfileBase] = None
    reason: str = "No reason provided"

class WorkerResponse(WorkerBase):
    id: int
    salary_profile: Optional[SalaryProfileBase] = None
    attendance: Optional[List[dict]] = None
    
    class Config:
        from_attributes = True

from datetime import datetime
from typing import List

class JobPhotoBase(CamelModel):
    photo_url: str
    photo_type: str
    timestamp: Optional[datetime] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    remarks: Optional[str] = None

class JobPhotoCreate(JobPhotoBase):
    pass

class JobPhoto(JobPhotoBase):
    id: int
    job_id: int
    uploaded_by_id: Optional[int] = None

    class Config:
        from_attributes = True

class WorkerJobBase(CamelModel):
    id: int
    vehicle_id: int
    stage: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    job_number: Optional[str] = None
    customer: Optional[str] = None
    site: Optional[str] = None
    priority: Optional[str] = None
    instructions: Optional[str] = None
    required_material: Optional[str] = None
    machine_required: Optional[str] = None
    qc_checklist_url: Optional[str] = None
    drawing_url: Optional[str] = None
    progress_percent: Optional[int] = None
    assigned_date: Optional[datetime] = None
    expected_completion: Optional[datetime] = None

class WorkerJob(WorkerJobBase):
    photos: List[JobPhoto] = []

    class Config:
        from_attributes = True

class WorkerDashboardStats(CamelModel):
    present_days: int
    absent_days: int
    leave_days: int
    ot_hours: float
    sunday_worked: int
    total_assigned_jobs: int
    pending_jobs: int
    in_progress_jobs: int
    completed_today: int

class PerformanceStats(CamelModel):
    jobs_completed: int
    avg_completion_time_hrs: float
    attendance_percent: float
    ot_hours: float
    performance_score: int
    monthly_trend: str

class PhotoUploadResponse(CamelModel):
    message: str
    photo: JobPhoto
