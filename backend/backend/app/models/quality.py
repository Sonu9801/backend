from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class QCRecord(Base):
    __tablename__ = "qc_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    stage = Column(String, nullable=False) # e.g. "fabrication"
    status = Column(String, default="Pending") # Pending, In Progress, Passed, Failed, Rework
    
    expected_time = Column(DateTime, nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    
    # Store the actual checklist dynamically
    checklist = Column(JSON, default=list)
    photos = Column(JSON, default=list)
    signature = Column(JSON, nullable=True)
    
    # Legacy fields mapping
    inspector_name = Column(String, nullable=True)
    inspected_at = Column(DateTime, nullable=True)
    result = Column(String, nullable=True)  # Pass, Fail
    defects_found = Column(JSON, default=list)  # Legacy
    notes = Column(Text, nullable=True)

    # Relationships
    vehicle = relationship("Vehicle", back_populates="qc_records")
    inspector = relationship("User", foreign_keys=[inspector_id])
    defects = relationship("DefectRecord", back_populates="qc_record", cascade="all, delete-orphan")

class DefectRecord(Base):
    __tablename__ = "defect_records"
    
    id = Column(Integer, primary_key=True, index=True)
    qc_record_id = Column(Integer, ForeignKey("qc_records.id", ondelete="CASCADE"), nullable=False)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    defect_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    responsible_department = Column(String, nullable=True)
    responsible_worker_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    target_resolution_date = Column(DateTime, nullable=True)
    status = Column(String, default="Open") # Open, Resolved
    
    qc_record = relationship("QCRecord", back_populates="defects")
    vehicle = relationship("Vehicle")
    worker = relationship("User", foreign_keys=[responsible_worker_id])
