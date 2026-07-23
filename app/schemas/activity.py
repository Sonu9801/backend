from datetime import datetime
from typing import Optional
from app.schemas.base import CamelModel

class ActivityEventBase(CamelModel):
    event_type: str
    description: str
    vehicle_id: Optional[int] = None
    worker_id: Optional[int] = None
    timestamp: datetime
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    edited_by: Optional[str] = None
    reason: Optional[str] = None

class ActivityEventCreate(ActivityEventBase):
    pass

class ActivityEventResponse(ActivityEventBase):
    id: int
