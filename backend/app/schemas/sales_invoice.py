from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime
from app.models.sales_invoice import SalesPaymentStatus, SalesApprovalStatus

class SalesInvoiceAuditBase(BaseModel):
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    edited_by: str
    reason: Optional[str] = None

class SalesInvoiceAuditResponse(SalesInvoiceAuditBase):
    id: int
    invoice_id: int
    edited_date: datetime
    
    model_config = ConfigDict(from_attributes=True)

class SalesInvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_gstin: Optional[str] = None
    invoice_date: Optional[date] = None
    po_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    oem: Optional[str] = None
    hsn_sac: Optional[str] = None
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    gst_amount: float = 0.0
    subtotal: float = 0.0
    grand_total: float = 0.0
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    work_type: Optional[str] = None
    description_work_details: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    rate: Optional[float] = None
    remarks: Optional[str] = None
    
    payment_status: SalesPaymentStatus = SalesPaymentStatus.PENDING
    approval_status: SalesApprovalStatus = SalesApprovalStatus.PENDING_REVIEW
    finance_remarks: Optional[str] = None
    received_amount: float = 0.0
    pending_amount: float = 0.0
    outstanding_amount: float = 0.0
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None
    transaction_reference: Optional[str] = None

class SalesInvoiceCreate(SalesInvoiceBase):
    file_path: Optional[str] = "manual_entry"
    file_hash: Optional[str] = None
    ocr_confidence_score: float = 0.0

class SalesInvoiceUpdate(BaseModel):
    payment_status: Optional[SalesPaymentStatus] = None
    approval_status: Optional[SalesApprovalStatus] = None
    finance_remarks: Optional[str] = None
    received_amount: Optional[float] = None
    pending_amount: Optional[float] = None
    outstanding_amount: Optional[float] = None
    payment_date: Optional[date] = None
    payment_mode: Optional[str] = None
    transaction_reference: Optional[str] = None
    
    # Allow correction of OCR fields if needed
    invoice_number: Optional[str] = None
    customer_name: Optional[str] = None
    customer_gstin: Optional[str] = None
    invoice_date: Optional[date] = None
    po_number: Optional[str] = None
    vehicle_number: Optional[str] = None
    oem: Optional[str] = None
    hsn_sac: Optional[str] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    gst_amount: Optional[float] = None
    subtotal: Optional[float] = None
    grand_total: Optional[float] = None
    payment_terms: Optional[str] = None
    due_date: Optional[date] = None
    work_type: Optional[str] = None
    description_work_details: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    rate: Optional[float] = None
    remarks: Optional[str] = None

class SalesInvoiceResponse(SalesInvoiceBase):
    id: int
    file_path: str
    ocr_confidence_score: float
    created_at: datetime
    updated_at: datetime
    audit_logs: list[SalesInvoiceAuditResponse] = []
    
    model_config = ConfigDict(from_attributes=True)
