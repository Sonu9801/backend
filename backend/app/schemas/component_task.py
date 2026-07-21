from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.schemas.user import UserResponse

class ComponentTaskBase(BaseModel):
    component_type: str
    component_number: str

class ComponentTaskCreate(ComponentTaskBase):
    pass

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

    class Config:
        from_attributes = True
