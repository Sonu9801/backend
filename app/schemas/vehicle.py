from datetime import datetime
from typing import Optional, List
from app.schemas.base import CamelModel
from pydantic import model_validator, Field, field_validator
from typing import Any

class VehicleBase(CamelModel):
    tracking_id: str
    vehicle_number: str
    product_category: str
    oem_name: str
    priority: str = "Normal"
    current_stage: str = "oem"
    progress_percent: int = 0
    notes: Optional[str] = None
    received_at: datetime
    estimated_delivery: datetime

    # OEM Collaboration / Logistics Fields
    driver_name: Optional[str] = None
    driver_mobile_number: Optional[str] = None
    transport_company: Optional[str] = None
    truck_number: Optional[str] = None
    lr_number: Optional[str] = None
    invoice_number: Optional[str] = None
    dispatch_challan_number: Optional[str] = None
    dispatch_date_time: Optional[datetime] = None
    expected_arrival_date_time: Optional[datetime] = None
    documents_url: Optional[str] = None
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Verification Fields
    verification_status: Optional[str] = "pending"
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    arrival_photos: Optional[str] = None
    verification_notes: Optional[str] = None
    platform_number: Optional[str] = None
    chassis_number: Optional[str] = None
    vin: Optional[str] = None
    dealer_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_type: Optional[str] = None
    submitted_by_oem: Optional[str] = None
    submitted_at: Optional[datetime] = None
    gate_entry_time: Optional[datetime] = None
    gate_entry_number: Optional[str] = None
    hold_reason: Optional[str] = None
    expected_resolution: Optional[str] = None
    dispatch_location: Optional[str] = None
    current_location: Optional[str] = None
    arrival_location: Optional[str] = None
    dispatch_coordinates: Optional[str] = None
    arrival_coordinates: Optional[str] = None

    @field_validator("verification_status", mode="before")
    @classmethod
    def set_default_verification_status(cls, v: Any) -> str:
        if v is None:
            return "pending"
        return v

class VehicleCreate(VehicleBase):
    assigned_worker_ids: Optional[List[int]] = []

class VehicleUpdate(CamelModel):
    tracking_id: Optional[str] = None
    vehicle_number: Optional[str] = None
    product_category: Optional[str] = None
    oem_name: Optional[str] = None
    priority: Optional[str] = None
    current_stage: Optional[str] = None
    progress_percent: Optional[int] = None
    notes: Optional[str] = None
    reason: Optional[str] = None
    received_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    assigned_worker_ids: Optional[List[int]] = None
    
    driver_name: Optional[str] = None
    driver_mobile_number: Optional[str] = None
    transport_company: Optional[str] = None
    truck_number: Optional[str] = None
    lr_number: Optional[str] = None
    invoice_number: Optional[str] = None
    dispatch_challan_number: Optional[str] = None
    dispatch_date_time: Optional[datetime] = None
    expected_arrival_date_time: Optional[datetime] = None
    documents_url: Optional[str] = None
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Verification Fields
    verification_status: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    arrival_time: Optional[datetime] = None
    arrival_photos: Optional[str] = None
    verification_notes: Optional[str] = None
    platform_number: Optional[str] = None
    chassis_number: Optional[str] = None
    vin: Optional[str] = None
    dealer_name: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_type: Optional[str] = None
    submitted_by_oem: Optional[str] = None
    submitted_at: Optional[datetime] = None
    gate_entry_time: Optional[datetime] = None
    gate_entry_number: Optional[str] = None
    hold_reason: Optional[str] = None
    expected_resolution: Optional[str] = None
    dispatch_location: Optional[str] = None
    current_location: Optional[str] = None
    arrival_location: Optional[str] = None
    dispatch_coordinates: Optional[str] = None
    arrival_coordinates: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: int
    assigned_worker_ids: List[int] = []

    @model_validator(mode="before")
    @classmethod
    def extract_worker_ids(cls, data):
        # Handle SQLAlchemy ORM objects
        if not isinstance(data, dict) and hasattr(data, "workers"):
            workers = data.workers or []
            data.assigned_worker_ids = [w.id for w in workers]
        # Handle dictionary representations
        elif isinstance(data, dict):
            if "workers" in data and "assigned_worker_ids" not in data:
                data["assigned_worker_ids"] = [
                    w["id"] if isinstance(w, dict) else w.id for w in data["workers"]
                ]
        return data
