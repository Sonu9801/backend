from pydantic import BaseModel
from typing import List

class FactorySettingsBase(BaseModel):
    facility_name: str
    address: str
    operating_hours: str
    timezone: str
    departments: List[str]

class FactorySettingsCreate(FactorySettingsBase):
    pass

class FactorySettingsUpdate(FactorySettingsBase):
    pass

class FactorySettingsResponse(FactorySettingsBase):
    id: int

    class Config:
        from_attributes = True
