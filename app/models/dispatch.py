from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class DispatchRecord(Base):
    __tablename__ = "dispatch_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    scheduled_date = Column(DateTime, nullable=False)
    carrier = Column(String, nullable=False)
    status = Column(String, default="Scheduled")  # Scheduled, InTransit, Delivered
    destination = Column(String, nullable=False)
    tracking_number = Column(String, nullable=False)

    # Delivery tracking fields
    delivered_time = Column(DateTime, nullable=True)
    receiver_name = Column(String, nullable=True)
    receiver_signature = Column(Text, nullable=True) # JSON or Base64 string
    delivery_photo = Column(String, nullable=True) # URL
    delivery_remarks = Column(Text, nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="dispatch_records")
