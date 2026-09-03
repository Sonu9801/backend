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
    tracking_number: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    chassis_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    oem_name: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    truck_number: Optional[str] = None
    lr_number: Optional[str] = None
    invoice_number: Optional[str] = None
    dispatch_challan_number: Optional[str] = None
    reason: Optional[str] = None
    delivered_time: Optional[datetime] = None
    receiver_name: Optional[str] = None
    receiver_signature: Optional[str] = None
    delivery_photo: Optional[str] = None
    delivery_remarks: Optional[str] = None

class DispatchRecordResponse(DispatchRecordBase):
    id: int
    vehicle_number: Optional[str] = None
    chassis_number: Optional[str] = None
    oem_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    product_category: Optional[str] = None
    vin: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    truck_number: Optional[str] = None
    lr_number: Optional[str] = None
    invoice_number: Optional[str] = None
    dispatch_challan_number: Optional[str] = None
    tracking_id: Optional[str] = None

