from pydantic import BaseModel
from typing import List, Optional
from app.schemas.base import CamelModel

class FactorySettingsBase(CamelModel):
    facility_name: Optional[str] = "FoxFlow Manufacturing Plant"
    address: Optional[str] = "Industrial Area, Sector 59, Faridabad"
    operating_hours: Optional[str] = "09:30 AM - 06:00 PM"
    timezone: Optional[str] = "Asia/Kolkata (IST)"
    departments: Optional[List[str]] = ["Fabrication", "Paint", "Assembly", "Quality", "Dispatch"]

class FactorySettingsCreate(FactorySettingsBase):
    pass

class FactorySettingsUpdate(FactorySettingsBase):
    pass

class FactorySettingsResponse(FactorySettingsBase):
    id: int

    class Config:
        from_attributes = True
