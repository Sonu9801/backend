from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.invoice import PaymentStatus, ApprovalStatus

class InvoiceAuditBase(BaseModel):
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    edited_by: str
    reason: Optional[str] = None

class InvoiceAuditResponse(InvoiceAuditBase):
    id: int
    invoice_id: int
    edited_date: datetime
    
    model_config = ConfigDict(from_attributes=True)

class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_date: Optional[date] = None
    hsn_sac: Optional[str] = None
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    gst_amount: float = 0.0
    subtotal: float = 0.0
    grand_total: float = 0.0
    
    expense_category: Optional[str] = None
    department: Optional[str] = None
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    approval_status: ApprovalStatus = ApprovalStatus.PENDING_REVIEW
    finance_remarks: Optional[str] = None

class InvoiceCreate(InvoiceBase):
    file_path: Optional[str] = "manual_entry"
    file_hash: Optional[str] = None
    ocr_confidence_score: float = 0.0

class InvoiceUpdate(BaseModel):
    expense_category: Optional[str] = None
    department: Optional[str] = None
    payment_status: Optional[PaymentStatus] = None
    approval_status: Optional[ApprovalStatus] = None
    finance_remarks: Optional[str] = None
    
    # Allow correction of OCR fields if needed
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_gstin: Optional[str] = None
    invoice_date: Optional[date] = None
    hsn_sac: Optional[str] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    gst_amount: Optional[float] = None
    subtotal: Optional[float] = None
    grand_total: Optional[float] = None

class InvoiceResponse(InvoiceBase):
    id: int
    file_path: str
    ocr_confidence_score: float
    created_at: datetime
    updated_at: datetime
    audit_logs: list[InvoiceAuditResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
