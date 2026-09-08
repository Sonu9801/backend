from pydantic import BaseModel, field_serializer
from typing import Optional, List
from datetime import datetime, timezone
from app.schemas.user import UserResponse

class ComponentTaskBase(BaseModel):
    component_type: str
    component_number: str

class ComponentTaskCreate(ComponentTaskBase):
    partner_id: Optional[int] = None

class ComponentTaskUpdate(BaseModel):
    component_type: Optional[str] = None
    component_number: Optional[str] = None
    partner_id: Optional[int] = None

class ComponentTaskSubmit(BaseModel):
    photo_proof_url: str
    notes: Optional[str] = None

class ComponentTaskResponse(ComponentTaskBase):
    id: int
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    photo_proof_url: Optional[str]
    notes: Optional[str]
    workers: List[UserResponse] = []

    @field_serializer('start_time', 'end_time')
    def serialize_datetime(self, dt: Optional[datetime], _info):
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    class Config:
        from_attributes = True
