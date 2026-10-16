from sqlalchemy import Column, Integer, String, JSON, Float
from app.database import Base

class FactorySettings(Base):
    __tablename__ = "factory_settings"

    id = Column(Integer, primary_key=True, index=True)
    facility_name = Column(String, default="Fox Enterprises")
    geofence_center_lng = Column(Float, default=77.3090)
    operating_hours = Column(String, default="Mon-Sat 09:00-17:30")
    support_contact = Column(String, default="+91-9876543210")
    address = Column(String, default="Industrial Area, Sector 59, Faridabad")
    timezone = Column(String, default="Asia/Kolkata")
    departments = Column(JSON, default=["Fabrication", "Paint", "QC", "Dispatch", "Stores"])
