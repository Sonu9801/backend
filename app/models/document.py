from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class WorkerDocument(Base):
    __tablename__ = "worker_documents"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    document_type = Column(String, nullable=False) # Offer Letter, ID Card, Salary Slip, Policy, Training
    file_url = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    
    status = Column(String, default="Active")
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    worker = relationship("User", foreign_keys=[worker_id])
