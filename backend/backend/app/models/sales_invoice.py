from sqlalchemy import Column, Integer, String, Float, Date, Enum, DateTime
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.database import Base

class SalesPaymentStatus(str, enum.Enum):
    PENDING = "Pending"
    PARTIAL = "Partially Paid"
    PAID = "Paid"
    CANCELLED = "Cancelled"
    OVERDUE = "Overdue"

class SalesApprovalStatus(str, enum.Enum):
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    POSSIBLE_DUPLICATE = "Possible Duplicate"

class SalesInvoice(Base):
    __tablename__ = "sales_invoices"

    id = Column(Integer, primary_key=True, index=True)
    
    # OCR Extracted Fields
    invoice_number = Column(String, index=True, nullable=True)
    customer_name = Column(String, index=True, nullable=True)
    customer_gstin = Column(String, index=True, nullable=True)
    invoice_date = Column(Date, index=True, nullable=True)
    po_number = Column(String, index=True, nullable=True)
    vehicle_number = Column(String, index=True, nullable=True)
    oem = Column(String, index=True, nullable=True)
    hsn_sac = Column(String, nullable=True)
    cgst = Column(Float, default=0.0)
    sgst = Column(Float, default=0.0)
    igst = Column(Float, default=0.0)
    gst_amount = Column(Float, default=0.0)
    subtotal = Column(Float, default=0.0)
    grand_total = Column(Float, default=0.0)
    payment_terms = Column(String, nullable=True)
    due_date = Column(Date, index=True, nullable=True)
    work_type = Column(String, index=True, nullable=True)
    description_work_details = Column(String, nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String, nullable=True)
    rate = Column(Float, nullable=True)
    remarks = Column(String, nullable=True)
    
    # System Fields
    file_path = Column(String, nullable=False)
    file_hash = Column(String, index=True, nullable=True)
    ocr_confidence_score = Column(Float, default=0.0)
    
    # User Managed Fields
    payment_status = Column(Enum(SalesPaymentStatus), default=SalesPaymentStatus.PENDING, index=True)
    approval_status = Column(Enum(SalesApprovalStatus), default=SalesApprovalStatus.PENDING_REVIEW, index=True)
    finance_remarks = Column(String, nullable=True)
    received_amount = Column(Float, default=0.0)
    pending_amount = Column(Float, default=0.0)
    outstanding_amount = Column(Float, default=0.0)
    payment_date = Column(Date, nullable=True)
    payment_mode = Column(String, nullable=True)
    transaction_reference = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
