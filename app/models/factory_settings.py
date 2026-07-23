from sqlalchemy import Column, Integer, String, JSON, Float
from app.database import Base

class FactorySettings(Base):
    __tablename__ = "factory_settings"

    id = Column(Integer, primary_key=True, index=True)
    facility_name = Column(String, default="FoxFlow Manufacturing - Unit 1")
    geofence_center_lng = Column(Float, default=77.3090)
    operating_hours = Column(String, default="Mon-Sat 09:30-18:00")
    support_contact = Column(String, default="+91-9876543210")
    departments = Column(JSON, default=["Fabrication", "Paint", "QC", "Dispatch", "Stores"])
