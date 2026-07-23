from datetime import datetime
from typing import Optional
from app.schemas.base import CamelModel

class DispatchRecordBase(CamelModel):
    vehicle_id: int
    scheduled_date: datetime
    carrier: str
    status: str = "Scheduled"  # Scheduled, InTransit, Delivered
    destination: str
    tracking_number: str
    
    # Delivery tracking fields
    delivered_time: Optional[datetime] = None
    receiver_name: Optional[str] = None
    receiver_signature: Optional[str] = None
    delivery_photo: Optional[str] = None
    delivery_remarks: Optional[str] = None

class DispatchRecordCreate(DispatchRecordBase):
    pass

class DispatchRecordUpdate(CamelModel):
    status: Optional[str] = None
    carrier: Optional[str] = None
    destination: Optional[str] = None
    reason: Optional[str] = None
    delivered_time: Optional[datetime] = None
    receiver_name: Optional[str] = None
    receiver_signature: Optional[str] = None
    delivery_photo: Optional[str] = None
    delivery_remarks: Optional[str] = None

class DispatchRecordResponse(DispatchRecordBase):
    id: int
