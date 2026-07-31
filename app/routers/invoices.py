from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
import os
import shutil
import uuid
from datetime import datetime, date, timedelta

from app.database import get_db
from app.models.user import User
from app.models.invoice import Invoice, PaymentStatus, ApprovalStatus
from app.models.invoice_audit import InvoiceAudit
from app.models.activity import ActivityEvent
from app.models.notification import Notification
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceBase
from app.services.ocr import extract_invoice_data
from app.auth import get_current_user
from app.services.websocket_manager import manager
from app.services.duplicate_detection import DuplicateDetectionService
import asyncio
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/invoices", tags=["Invoices"])

UPLOAD_DIR = "uploads/invoices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=InvoiceCreate)
async def upload_invoice(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        if current_user.role not in ["admin", "finance_manager", "owner"]:
            raise HTTPException(status_code=403, detail="Not authorized")

        # Save file
        current_month_year = datetime.now().strftime("%Y/%m")
        save_dir = os.path.join(UPLOAD_DIR, current_month_year)
        os.makedirs(save_dir, exist_ok=True)
        
        filename = file.filename if file.filename else "image.jpg"
        file_extension = filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = os.path.join(save_dir, unique_filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        relative_path = f"/uploads/invoices/{current_month_year}/{unique_filename}"
        
        # Layer 1: File Hash Validation
        file_hash = DuplicateDetectionService.calculate_file_hash(file_path)
        if DuplicateDetectionService.check_hash_exists(db, file_hash):
            os.remove(file_path)  # Cleanup duplicate file
            raise HTTPException(
                status_code=409, 
                detail="This invoice has already been uploaded."
            )
        
        # Process OCR asynchronously in a threadpool to avoid blocking the server
        extracted_data = await run_in_threadpool(extract_invoice_data, file_path)
        
        # Log upload and OCR
        activity = ActivityEvent(
            event_type="invoice_uploaded",
            description=f"Invoice uploaded and OCR processed by {current_user.name}",
            timestamp=datetime.utcnow(),
            edited_by=current_user.name
        )
        db.add(activity)
        db.commit()
        
        await manager.broadcast({"type": "INVOICE_UPLOADED"})
        
        return InvoiceCreate(
            file_path=relative_path,
            file_hash=file_hash,
            **extracted_data
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"500 ERROR IN UPLOAD: {error_trace}")
        raise HTTPException(status_code=400, detail=f"DEBUG ERROR: {str(e)} | TRACE: {error_trace}")

@router.post("")
async def create_invoice(
    invoice: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ["admin", "finance_manager", "owner"]:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        # Layer 2: Invoice Number + Vendor Validation
        if DuplicateDetectionService.check_invoice_number(db, invoice.invoice_number, invoice.vendor_name):
            raise HTTPException(
                status_code=409, 
                detail="This invoice has already been uploaded."
            )

        # Layer 3: Business Rules Exact Match Validation
        if DuplicateDetectionService.check_business_rules(db, invoice.model_dump()):
            raise HTTPException(
                status_code=409, 
                detail="This invoice has already been uploaded."
            )
                
        db_invoice = Invoice(**invoice.model_dump())
        
        # Layer 4: OCR Similarity Validation
        if DuplicateDetectionService.calculate_similarity(db, invoice.model_dump()):
            db_invoice.approval_status = ApprovalStatus.POSSIBLE_DUPLICATE
        elif db_invoice.ocr_confidence_score >= 90:
            db_invoice.approval_status = ApprovalStatus.APPROVED
        else:
            db_invoice.approval_status = ApprovalStatus.PENDING_REVIEW
            
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)
        
        # Notification & WebSocket
        if db_invoice.approval_status == ApprovalStatus.PENDING_REVIEW:
            notif = Notification(
                type="warning",
                title="Invoice Pending Review",
                message=f"Invoice {db_invoice.invoice_number} from {db_invoice.vendor_name} requires manual review.",
                module="invoices",
                target_url=f"/invoices/{db_invoice.id}",
                assigned_role="finance_manager"
            )
            db.add(notif)
            db.commit()
            await manager.broadcast({"type": "NEW_NOTIFICATION"})
            
        return {"id": db_invoice.id, "status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"500 ERROR IN CREATE: {error_trace}")
        raise HTTPException(status_code=400, detail=f"DEBUG ERROR: {str(e)} | TRACE: {error_trace}")

@router.get("")
def get_invoices(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    approval_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    vendor: Optional[str] = None,
    department: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Invoice)

    if search:
        query = query.filter(
            or_(
                Invoice.invoice_number.ilike(f"%{search}%"),
                Invoice.vendor_name.ilike(f"%{search}%"),
                Invoice.vendor_gstin.ilike(f"%{search}%"),
                Invoice.finance_remarks.ilike(f"%{search}%"),
            )
        )

    if approval_status:
        query = query.filter(Invoice.approval_status == approval_status)
    if payment_status:
        query = query.filter(Invoice.payment_status == payment_status)
    if vendor:
        query = query.filter(Invoice.vendor_name == vendor)
    if department:
        query = query.filter(Invoice.department == department)
    if category:
        query = query.filter(Invoice.expense_category == category)

    total = query.count()
    total_pages = max(1, -(-total // page_size))
    offset = (page - 1) * page_size
    items = query.order_by(desc(Invoice.created_at)).offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/dashboard-stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    today = date.today()
    this_month = today.replace(day=1)
    
    today_uploads = db.query(Invoice).filter(func.date(Invoice.created_at) == today).count()
    today_expenses = db.query(func.sum(Invoice.grand_total)).filter(func.date(Invoice.created_at) == today).scalar() or 0
    monthly_expenses = db.query(func.sum(Invoice.grand_total)).filter(func.date(Invoice.created_at) >= this_month).scalar() or 0
    pending_review = db.query(Invoice).filter(Invoice.approval_status == ApprovalStatus.PENDING_REVIEW).count()
    
    approved = db.query(Invoice).filter(Invoice.approval_status == ApprovalStatus.APPROVED).count()
    rejected = db.query(Invoice).filter(Invoice.approval_status == ApprovalStatus.REJECTED).count()
    paid = db.query(Invoice).filter(Invoice.payment_status == PaymentStatus.PAID).count()
    unpaid = db.query(Invoice).filter(Invoice.payment_status == PaymentStatus.UNPAID).count()
    gst_this_month = db.query(func.sum(Invoice.gst_amount)).filter(func.date(Invoice.created_at) >= this_month).scalar() or 0

    return {
        "today_uploads": today_uploads,
        "today_expenses": today_expenses,
        "monthly_expenses": monthly_expenses,
        "pending_review": pending_review,
        "approved": approved,
        "rejected": rejected,
        "paid": paid,
        "unpaid": unpaid,
        "gst_this_month": gst_this_month
    }

@router.get("/analytics")
def get_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Department Distribution
    dept_dist = db.query(Invoice.department, func.sum(Invoice.grand_total).label("total")).group_by(Invoice.department).all()
    
    # Category Distribution
    cat_dist = db.query(Invoice.expense_category, func.sum(Invoice.grand_total).label("total")).group_by(Invoice.expense_category).all()
    
    # Top Vendors
    top_vendors = db.query(Invoice.vendor_name, func.sum(Invoice.grand_total).label("total")).group_by(Invoice.vendor_name).order_by(desc("total")).limit(5).all()
    
    # Monthly Trend (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    monthly_trend = db.query(
        func.to_char(Invoice.invoice_date, 'YYYY-MM').label("month"),
        func.sum(Invoice.grand_total).label("total")
    ).filter(Invoice.invoice_date >= six_months_ago).group_by("month").order_by("month").all()

    return {
        "departmentDistribution": [{"name": d[0] or "Unassigned", "value": d[1]} for d in dept_dist],
        "categoryDistribution": [{"name": c[0] or "Unassigned", "value": c[1]} for c in cat_dist],
        "topVendors": [{"name": v[0] or "Unknown", "value": v[1]} for v in top_vendors],
        "monthlyTrend": [{"month": m[0], "total": m[1]} for m in monthly_trend]
    }

@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice

@router.patch("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int, 
    update_data: InvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "finance_manager", "owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, new_value in update_dict.items():
        old_value = getattr(db_invoice, key)
        if old_value != new_value:
            # Audit log
            audit = InvoiceAudit(
                invoice_id=db_invoice.id,
                field_name=key,
                old_value=str(old_value) if old_value is not None else "",
                new_value=str(new_value) if new_value is not None else "",
                edited_by=current_user.name,
                reason="Manual Edit"
            )
            db.add(audit)
            setattr(db_invoice, key, new_value)
            
            # Activity Log for status changes
            if key == "approval_status":
                act = ActivityEvent(
                    event_type="invoice_approval_changed",
                    description=f"Invoice {db_invoice.invoice_number} marked as {new_value} by {current_user.name}",
                    timestamp=datetime.utcnow(),
                    edited_by=current_user.name
                )
                db.add(act)
                # Notification
                notif = Notification(
                    type="success" if new_value == ApprovalStatus.APPROVED else "error",
                    title="Invoice Approval Status",
                    message=f"Invoice {db_invoice.invoice_number} is now {new_value}.",
                    module="invoices",
                    target_url=f"/invoices/{db_invoice.id}",
                    assigned_role="owner"
                )
                db.add(notif)
                
            if key == "payment_status":
                act = ActivityEvent(
                    event_type="invoice_payment_changed",
                    description=f"Invoice {db_invoice.invoice_number} payment status updated to {new_value} by {current_user.name}",
                    timestamp=datetime.utcnow(),
                    edited_by=current_user.name
                )
                db.add(act)
        
    db.commit()
    db.refresh(db_invoice)
    
    await manager.broadcast({"type": "INVOICE_UPDATED"})
    await manager.broadcast({"type": "NEW_NOTIFICATION"})
    
    return db_invoice

@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "finance_manager", "owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    db.delete(db_invoice)
    db.commit()
    
    await manager.broadcast({"type": "INVOICE_UPDATED"})
    
    return {"message": "Invoice deleted"}

