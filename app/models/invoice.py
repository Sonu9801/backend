from sqlalchemy import Column, Integer, String, Float, Date, Enum, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base

class PaymentStatus(str, enum.Enum):
    UNPAID = "Unpaid"
    PARTIAL = "Partial"
    PAID = "Paid"

class ApprovalStatus(str, enum.Enum):
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    POSSIBLE_DUPLICATE = "Possible Duplicate"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    
    # OCR Extracted Fields
    invoice_number = Column(String, index=True, nullable=True)
    vendor_name = Column(String, index=True, nullable=True)
    vendor_gstin = Column(String, index=True, nullable=True)
    invoice_date = Column(Date, index=True, nullable=True)
    hsn_sac = Column(String, nullable=True)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    igst = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    
    # System Fields
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=True)
    ocr_confidence_score = Column(Float, default=0.0)
    
    # User Managed Fields
    expense_category = Column(String, index=True, nullable=True)
    department = Column(String, index=True, nullable=True)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, index=True)
    approval_status = Column(Enum(ApprovalStatus), default=ApprovalStatus.PENDING_REVIEW, index=True)
    finance_remarks = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
