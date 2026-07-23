from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, nullable=False)  # e.g., worker_started, qc_passed, qc_failed, etc.
    description = Column(Text, nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    worker_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, nullable=False)
    
    # Audit log fields
    old_value = Column(Text, nullable=True) # Stored as JSON string
    new_value = Column(Text, nullable=True) # Stored as JSON string
    edited_by = Column(String, nullable=True) # Name or Username of the editor
    reason = Column(Text, nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="activities")
    worker = relationship("User", back_populates="activities")
