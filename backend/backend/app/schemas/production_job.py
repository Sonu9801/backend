from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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

    class Config:
        from_attributes = True
