from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class JobPhoto(Base):
    __tablename__ = "job_photos"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("production_jobs.id", ondelete="CASCADE"), nullable=False)
    photo_url = Column(Text, nullable=False)
    photo_type = Column(String, nullable=False) # 'progress' or 'completion'
    timestamp = Column(DateTime, default=datetime.utcnow)
    gps_lat = Column(Float, nullable=True)
    gps_lng = Column(Float, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    remarks = Column(Text, nullable=True)

    job = relationship("ProductionJob", back_populates="photos")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
