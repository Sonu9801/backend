from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime, timezone
from app.schemas.user import UserResponse

class ProductionJobPhoto(BaseModel):
    id: int
    photo_url: str
    photo_type: str
    timestamp: Optional[datetime] = None
    gps_lat: Optional[float] = None
    gps_lng: Optional[float] = None
    remarks: Optional[str] = None

    class Config:
        from_attributes = True

class SimpleVehicleInfo(BaseModel):
    id: int
    vehicle_number: Optional[str] = None
    chassis_number: Optional[str] = None
    platform_number: Optional[str] = None
    model_name: Optional[str] = None

    class Config:
        from_attributes = True

class ProductionJobBase(BaseModel):
    vehicle_id: int
    stage: str
    status: Optional[str] = "not_started"
    supervisor_id: Optional[int] = None
    expected_duration_minutes: Optional[int] = 120
    assignment_source: Optional[str] = "supervisor"

class ProductionJobCreate(ProductionJobBase):
    worker_ids: List[int] = []

class ProductionJobUpdate(BaseModel):
    status: Optional[str] = None
    photo_proof_url: Optional[str] = None
    comments: Optional[str] = None

class ProductionJobResponse(ProductionJobBase):
    id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    photo_proof_url: Optional[str] = None
    comments: Optional[str] = None
    photos: List[ProductionJobPhoto] = []
    workers: List[UserResponse] = []
    vehicle: Optional[SimpleVehicleInfo] = None

    @field_serializer('start_time', 'end_time')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True

