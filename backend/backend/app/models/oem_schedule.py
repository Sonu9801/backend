from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.database import Base

class OEMSchedule(Base):
    __tablename__ = "oem_schedules"

    id = Column(Integer, primary_key=True, index=True)
    oem_name = Column(String, index=True)
    dealer_name = Column(String)
    expected_date = Column(DateTime, nullable=False)
    quantity = Column(Integer, default=1)
    product_category = Column(String)
    status = Column(String, default="Pending") # Pending, Arrived, Delayed

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
