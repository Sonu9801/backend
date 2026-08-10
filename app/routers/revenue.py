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
from app.models.sales_invoice import SalesInvoice, SalesPaymentStatus, SalesApprovalStatus
from app.models.sales_invoice_audit import SalesInvoiceAudit
from app.models.activity import ActivityEvent
from app.models.notification import Notification
from app.schemas.sales_invoice import SalesInvoiceCreate, SalesInvoiceUpdate, SalesInvoiceResponse, SalesInvoiceBase
from app.services.ocr import extract_invoice_data
from app.auth import get_current_user
from app.services.websocket_manager import manager
from app.services.duplicate_detection import DuplicateDetectionService
import asyncio
from fastapi.concurrency import run_in_threadpool

router = APIRouter(prefix="/revenue", tags=["Revenue"])

UPLOAD_DIR = "uploads/sales_invoices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=SalesInvoiceCreate)
async def upload_sales_invoice(
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
            
        relative_path = f"/uploads/sales_invoices/{current_month_year}/{unique_filename}"
        
        # Layer 1: File Hash Validation
        file_hash = DuplicateDetectionService.calculate_file_hash(file_path)
        if DuplicateDetectionService.check_hash_exists(db, file_hash, model_class=SalesInvoice):
            os.remove(file_path)  # Cleanup duplicate file
            raise HTTPException(
                status_code=409, 
                detail="This sales invoice has already been uploaded."
            )
        
        # Process OCR asynchronously in a threadpool to avoid blocking the server
        extracted_data = await run_in_threadpool(extract_invoice_data, file_path, "sales")
        
        # Log upload and OCR
        activity = ActivityEvent(
            event_type="sales_invoice_uploaded",
            description=f"Sales Bill uploaded and OCR processed by {current_user.name}",
            timestamp=datetime.utcnow(),
            edited_by=current_user.name
        )
        db.add(activity)
        db.commit()
        
        await manager.broadcast({"type": "SALES_INVOICE_UPLOADED"})
        
        return SalesInvoiceCreate(
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
        raise HTTPException(status_code=400, detail=f"DEBUG ERROR: {str(e)}")

@router.post("")
async def create_sales_invoice(
    invoice: SalesInvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        if current_user.role not in ["admin", "finance_manager", "owner"]:
            raise HTTPException(status_code=403, detail="Not authorized")
            
        # Layer 2: Invoice Number + Customer Validation
        if DuplicateDetectionService.check_invoice_number(db, invoice.invoice_number, invoice.customer_name, model_class=SalesInvoice):
            raise HTTPException(
                status_code=409, 
                detail="This sales invoice has already been uploaded."
            )

        # Layer 3: Business Rules Exact Match Validation
        if DuplicateDetectionService.check_business_rules(db, invoice.model_dump(), model_class=SalesInvoice):
            raise HTTPException(
                status_code=409, 
                detail="This sales invoice has already been uploaded."
            )
                
        db_invoice = SalesInvoice(**invoice.model_dump())
        
        # Set Outstanding Amount to Grand Total initially
        db_invoice.outstanding_amount = db_invoice.grand_total
        db_invoice.pending_amount = db_invoice.grand_total
        
        # Layer 4: OCR Similarity Validation
        if DuplicateDetectionService.calculate_similarity(db, invoice.model_dump(), model_class=SalesInvoice):
            db_invoice.approval_status = SalesApprovalStatus.POSSIBLE_DUPLICATE
        elif db_invoice.ocr_confidence_score >= 90:
            db_invoice.approval_status = SalesApprovalStatus.APPROVED
        else:
            db_invoice.approval_status = SalesApprovalStatus.PENDING_REVIEW
            
        db.add(db_invoice)
        db.commit()
        db.refresh(db_invoice)
        
        # Notification & WebSocket
        if db_invoice.approval_status == SalesApprovalStatus.PENDING_REVIEW:
            notif = Notification(
                type="warning",
                title="Sales Invoice Pending Review",
                message=f"Sales Bill {db_invoice.invoice_number} from {db_invoice.customer_name} requires manual review.",
                module="revenue",
                target_url=f"/revenue/{db_invoice.id}",
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
        raise HTTPException(status_code=400, detail=f"DEBUG ERROR: {str(e)}")

@router.get("")
def get_sales_invoices(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    approval_status: Optional[str] = None,
    payment_status: Optional[str] = None,
    customer: Optional[str] = None,
    oem: Optional[str] = None,
    work_type: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SalesInvoice)

    if search:
        query = query.filter(
            or_(
                SalesInvoice.invoice_number.ilike(f"%{search}%"),
                SalesInvoice.customer_name.ilike(f"%{search}%"),
                SalesInvoice.customer_gstin.ilike(f"%{search}%"),
                SalesInvoice.vehicle_number.ilike(f"%{search}%"),
                SalesInvoice.po_number.ilike(f"%{search}%"),
            )
        )

    if approval_status:
        query = query.filter(SalesInvoice.approval_status == approval_status)
    if payment_status:
        query = query.filter(SalesInvoice.payment_status == payment_status)
    if customer:
        query = query.filter(SalesInvoice.customer_name == customer)
    if oem:
        query = query.filter(SalesInvoice.oem == oem)
    if work_type:
        query = query.filter(SalesInvoice.work_type == work_type)
    from sqlalchemy.sql.functions import coalesce
    s_date = start_date or date_from
    e_date = end_date or date_to
    if s_date:
        query = query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) >= s_date)
    if e_date:
        query = query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) <= e_date)

    total = query.count()
    total_pages = max(1, -(-total // page_size))
    offset = (page - 1) * page_size
    items = query.order_by(desc(SalesInvoice.created_at)).offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/dashboard-stats")
def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.sql.functions import coalesce
    s_date = start_date or date_from
    e_date = end_date or date_to
    
    today = date.today()
    this_month = today.replace(day=1)
    
    query = db.query(SalesInvoice)
    if s_date:
        query = query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) >= s_date)
    if e_date:
        query = query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) <= e_date)
        
    total_invoices_count = query.count()
    total_revenue_all = query.with_entities(func.sum(SalesInvoice.grand_total)).scalar() or 0
    pending_review = query.filter(SalesInvoice.approval_status == SalesApprovalStatus.PENDING_REVIEW).count()
    approved = query.filter(SalesInvoice.approval_status == SalesApprovalStatus.APPROVED).count()
    rejected = query.filter(SalesInvoice.approval_status == SalesApprovalStatus.REJECTED).count()
    
    outstanding = query.with_entities(func.sum(SalesInvoice.outstanding_amount)).scalar() or 0
    received = query.with_entities(func.sum(SalesInvoice.received_amount)).scalar() or 0
    
    if s_date or e_date:
        today_uploads = total_invoices_count
        today_revenue = total_revenue_all
        monthly_revenue = total_revenue_all
    else:
        today_uploads = db.query(SalesInvoice).filter(func.date(SalesInvoice.created_at) == today).count()
        today_revenue = db.query(func.sum(SalesInvoice.grand_total)).filter(func.date(SalesInvoice.created_at) == today).scalar() or 0
        monthly_revenue = db.query(func.sum(SalesInvoice.grand_total)).filter(func.date(SalesInvoice.created_at) >= this_month).scalar() or 0

    average_invoice_value = total_revenue_all / total_invoices_count if total_invoices_count > 0 else 0
    collection_rate = (received / total_revenue_all * 100) if total_revenue_all > 0 else 0
    
    return {
        "today_uploads": today_uploads,
        "today_revenue": today_revenue,
        "monthly_revenue": monthly_revenue,
        "pending_review": pending_review,
        "approved": approved,
        "rejected": rejected,
        "outstanding": outstanding,
        "received": received,
        "average_invoice_value": average_invoice_value,
        "collection_rate": collection_rate
    }

@router.get("/analytics")
def get_analytics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy.sql.functions import coalesce
    s_date = start_date or date_from
    e_date = end_date or date_to
    
    base_query = db.query(SalesInvoice)
    if s_date:
        base_query = base_query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) >= s_date)
    if e_date:
        base_query = base_query.filter(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)) <= e_date)

    # OEM Distribution
    oem_dist = base_query.with_entities(SalesInvoice.oem, func.sum(SalesInvoice.grand_total).label("total")).group_by(SalesInvoice.oem).all()
    
    # Top Customers
    top_customers = base_query.with_entities(SalesInvoice.customer_name, func.sum(SalesInvoice.grand_total).label("total")).group_by(SalesInvoice.customer_name).order_by(desc("total")).limit(5).all()
    
    # Status Distribution (mapped to categoryDistribution for frontend)
    status_dist = base_query.with_entities(SalesInvoice.payment_status, func.sum(SalesInvoice.grand_total).label("total")).group_by(SalesInvoice.payment_status).all()
    
    # Monthly Trend
    if s_date or e_date:
        monthly_trend = base_query.with_entities(
            func.to_char(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)), 'YYYY-MM').label("month"),
            func.sum(SalesInvoice.grand_total).label("total")
        ).group_by("month").order_by("month").all()
    else:
        six_months_ago = datetime.now() - timedelta(days=180)
        monthly_trend = db.query(
            func.to_char(SalesInvoice.invoice_date, 'YYYY-MM').label("month"),
            func.sum(SalesInvoice.grand_total).label("total")
        ).filter(SalesInvoice.invoice_date >= six_months_ago).group_by("month").order_by("month").all()
    
    # Work Type Distribution
    work_type_dist = base_query.with_entities(SalesInvoice.work_type, func.sum(SalesInvoice.grand_total).label("total")).group_by(SalesInvoice.work_type).all()
    
    # Outstanding Trend
    if s_date or e_date:
        outstanding_trend = base_query.with_entities(
            func.to_char(coalesce(SalesInvoice.invoice_date, func.date(SalesInvoice.created_at)), 'YYYY-MM').label("month"),
            func.sum(SalesInvoice.outstanding_amount).label("total")
        ).group_by("month").order_by("month").all()
    else:
        six_months_ago = datetime.now() - timedelta(days=180)
        outstanding_trend = db.query(
            func.to_char(SalesInvoice.invoice_date, 'YYYY-MM').label("month"),
            func.sum(SalesInvoice.outstanding_amount).label("total")
        ).filter(SalesInvoice.invoice_date >= six_months_ago).group_by("month").order_by("month").all()

    return {
        "oemDistribution": [{"name": d[0] or "Unassigned", "value": d[1]} for d in oem_dist],
        "topCustomers": [{"name": v[0] or "Unknown", "value": v[1]} for v in top_customers],
        "categoryDistribution": [{"name": s[0] or "Unassigned", "value": s[1]} for s in status_dist],
        "monthlyTrend": [{"month": m[0], "total": m[1]} for m in monthly_trend],
        "workTypeDistribution": [{"name": w[0] or "Unassigned", "value": w[1]} for w in work_type_dist],
        "outstandingTrend": [{"month": o[0], "total": o[1]} for o in outstanding_trend]
    }

@router.get("/{invoice_id}", response_model=SalesInvoiceResponse)
def get_sales_invoice(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invoice = db.query(SalesInvoice).filter(SalesInvoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Sales Invoice not found")
    return invoice

@router.patch("/{invoice_id}", response_model=SalesInvoiceResponse)
async def update_sales_invoice(
    invoice_id: int, 
    update_data: SalesInvoiceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "finance_manager", "owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_invoice = db.query(SalesInvoice).filter(SalesInvoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Sales Invoice not found")
        
    update_dict = update_data.model_dump(exclude_unset=True)
    
    for key, new_value in update_dict.items():
        old_value = getattr(db_invoice, key)
        if old_value != new_value:
            # Audit log
            audit = SalesInvoiceAudit(
                invoice_id=db_invoice.id,
                field_name=key,
                old_value=str(old_value) if old_value is not None else "",
                new_value=str(new_value) if new_value is not None else "",
                edited_by=current_user.name,
                reason="Manual Edit"
            )
            db.add(audit)
            setattr(db_invoice, key, new_value)
            
            # Additional logic for received amount
            if key == "received_amount":
                # auto calculate outstanding and pending
                db_invoice.outstanding_amount = max(0, db_invoice.grand_total - db_invoice.received_amount)
                db_invoice.pending_amount = db_invoice.outstanding_amount
                
                # Update payment status
                if db_invoice.outstanding_amount == 0:
                    db_invoice.payment_status = SalesPaymentStatus.PAID
                elif db_invoice.received_amount > 0:
                    db_invoice.payment_status = SalesPaymentStatus.PARTIAL
                    
            # Activity Log for status changes
            if key == "approval_status":
                act = ActivityEvent(
                    event_type="sales_invoice_approval_changed",
                    description=f"Sales Bill {db_invoice.invoice_number} marked as {new_value} by {current_user.name}",
                    timestamp=datetime.utcnow(),
                    edited_by=current_user.name
                )
                db.add(act)
                # Notification
                notif = Notification(
                    type="success" if new_value == SalesApprovalStatus.APPROVED else "error",
                    title="Sales Invoice Approval Status",
                    message=f"Sales Bill {db_invoice.invoice_number} is now {new_value}.",
                    module="revenue",
                    target_url=f"/revenue/{db_invoice.id}",
                    assigned_role="owner"
                )
                db.add(notif)
                
            if key == "payment_status":
                act = ActivityEvent(
                    event_type="sales_invoice_payment_changed",
                    description=f"Sales Bill {db_invoice.invoice_number} payment status updated to {new_value} by {current_user.name}",
                    timestamp=datetime.utcnow(),
                    edited_by=current_user.name
                )
                db.add(act)
        
    db.commit()
    db.refresh(db_invoice)
    
    await manager.broadcast({"type": "SALES_INVOICE_UPDATED"})
    await manager.broadcast({"type": "NEW_NOTIFICATION"})
    
    return db_invoice

@router.delete("/{invoice_id}")
async def delete_sales_invoice(
    invoice_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "finance_manager", "owner"]:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    db_invoice = db.query(SalesInvoice).filter(SalesInvoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Sales Invoice not found")
        
    db.delete(db_invoice)
    db.commit()
    
    await manager.broadcast({"type": "SALES_INVOICE_UPDATED"})
    
    return {"message": "Sales Invoice deleted"}
