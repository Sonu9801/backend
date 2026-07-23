from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from datetime import datetime

from app.database import Base

class SalesInvoiceAudit(Base):
    __tablename__ = "sales_invoice_audit"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("sales_invoices.id", ondelete="CASCADE"), index=True, nullable=False)
    
    field_name = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    
    edited_by = Column(String, nullable=False)
    edited_date = Column(DateTime, default=datetime.utcnow)
    reason = Column(String, nullable=True)

    sales_invoice = relationship("SalesInvoice", backref=backref("audit_logs", cascade="all, delete-orphan"))
