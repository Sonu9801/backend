import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import field_validator
from app.schemas.base import CamelModel

class DefectRecordBase(CamelModel):
    defect_type: str
    severity: str
    category: str
    description: str
    responsible_department: Optional[str] = None
    responsible_worker_id: Optional[int] = None
    target_resolution_date: Optional[datetime] = None
    status: str = "Open"

class DefectRecordCreate(DefectRecordBase):
    qc_record_id: int
    vehicle_id: int

class DefectRecordResponse(DefectRecordBase):
    id: int
    qc_record_id: int
    vehicle_id: int
    
class QCRecordBase(CamelModel):
    vehicle_id: int
    inspector_id: Optional[int] = None
    stage: str
    status: str = "Pending"
    expected_time: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    checklist: List[Dict[str, Any]] = []
    photos: List[str] = []
    signature: Optional[Dict[str, Any]] = None
    
    # Legacy fields
    inspector_name: Optional[str] = None
    inspected_at: Optional[datetime] = None
    result: Optional[str] = None
    defects_found: List[str] = []
    notes: Optional[str] = None

    @field_validator("defects_found", "checklist", "photos", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return []
        return v if v is not None else []

class QCRecordCreate(QCRecordBase):
    pass

class QCRecordUpdate(CamelModel):
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    checklist: Optional[List[Dict[str, Any]]] = None
    photos: Optional[List[str]] = None
    signature: Optional[Dict[str, Any]] = None
    inspector_name: Optional[str] = None
    inspected_at: Optional[datetime] = None
    result: Optional[str] = None
    defects_found: Optional[List[str]] = None
    notes: Optional[str] = None
    reason: Optional[str] = None

class QCRecordResponse(QCRecordBase):
    id: int
    defects: List[DefectRecordResponse] = []
