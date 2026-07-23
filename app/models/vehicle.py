from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from app.database import Base
from app.models.associations import vehicle_user_association

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(String, unique=True, index=True, nullable=False)
    vehicle_number = Column(String, nullable=False)
    product_category = Column(String, nullable=False)  # e.g., CargoBox, BatteryBox, etc.
    oem_name = Column(String, nullable=False)
    priority = Column(String, default="Normal")  # Normal, High, Urgent
    current_stage = Column(String, default="oem")
    qc_status = Column(String, default="Not Required") # Not Required, Pending, In Progress, Failed, Passed
    progress_percent = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False)
    estimated_delivery = Column(DateTime, nullable=False)

    # OEM Collaboration / Logistics Fields
    driver_name = Column(String, nullable=True)
    driver_mobile_number = Column(String, nullable=True)
    transport_company = Column(String, nullable=True)
    truck_number = Column(String, nullable=True)
    lr_number = Column(String, nullable=True)
    invoice_number = Column(String, nullable=True)
    dispatch_challan_number = Column(String, nullable=True)
    dispatch_date_time = Column(DateTime, nullable=True)
    expected_arrival_date_time = Column(DateTime, nullable=True)
    documents_url = Column(String, nullable=True) # Could be a comma separated list of URLs if needed
    remarks = Column(Text, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Verification Fields
    verification_status = Column(String, default="pending")
    verified_by = Column(String, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    arrival_time = Column(DateTime, nullable=True)
    arrival_photos = Column(Text, nullable=True) # JSON array
    verification_notes = Column(Text, nullable=True)
    platform_number = Column(String, nullable=True)
    chassis_number = Column(String, nullable=True)
    vin = Column(String, nullable=True)
    dealer_name = Column(String, nullable=True)
    vehicle_model = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=True)
    submitted_by_oem = Column(String, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    gate_entry_time = Column(DateTime, nullable=True)
    gate_entry_number = Column(String, nullable=True, unique=True, index=True)
    hold_reason = Column(Text, nullable=True)
    expected_resolution = Column(Text, nullable=True)
    
    # Locations
    dispatch_location = Column(String, nullable=True)
    current_location = Column(String, nullable=True)
    arrival_location = Column(String, nullable=True)
    dispatch_coordinates = Column(String, nullable=True)
    arrival_coordinates = Column(String, nullable=True)

    # Relationships
    workers = relationship(
        "User",
        secondary=vehicle_user_association,
        back_populates="vehicles"
    )
    qc_records = relationship("QCRecord", back_populates="vehicle", cascade="all, delete-orphan")
    dispatch_records = relationship("DispatchRecord", back_populates="vehicle", cascade="all, delete-orphan")
    activities = relationship("ActivityEvent", back_populates="vehicle", cascade="all, delete-orphan")
    production_jobs = relationship("ProductionJob", back_populates="vehicle", cascade="all, delete-orphan")
