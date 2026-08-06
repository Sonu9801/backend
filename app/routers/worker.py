from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.production_job import ProductionJob
from app.models.job_photo import JobPhoto
from app.models.attendance import Attendance
from app.schemas.worker import (
    WorkerJob,
    WorkerDashboardStats,
    PerformanceStats,
    JobPhoto as JobPhotoSchema,
    PhotoUploadResponse
)
from app.auth import get_current_active_user

router = APIRouter(prefix="/worker", tags=["Worker PWA"])

def get_current_worker(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get("/dashboard", response_model=WorkerDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    # Get current month start/end dates in Indian Standard Time (IST)
    ist_offset = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(ist_offset)
    today = now_ist.date()
    start_of_month = today.replace(day=1)

    # 1. Fetch monthly attendance records
    records = db.query(Attendance).filter(
        Attendance.worker_id == current_worker.id,
        Attendance.date >= start_of_month,
        Attendance.date <= today
    ).all()

    present_days = float(len([r for r in records if r.status in ["Present", "Late", "Sunday Work"]]))
    half_days = float(len([r for r in records if r.status == "Half Day"]))
    present_days += half_days * 0.5

    absent_days = float(len([r for r in records if r.status == "Absent"]))
    leave_days = float(len([r for r in records if r.status == "Leave"]))
    ot_hours = float(sum(r.ot_hours for r in records if r.ot_hours))
    
    sunday_worked = len([r for r in records if r.is_sunday and r.status in ["Present", "Late", "Sunday Work"]])

    # 2. Fetch assigned production jobs
    total_assigned = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=current_worker.id)
    ).count()

    pending = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=current_worker.id),
        ProductionJob.status.in_(["not_started", "assigned"])
    ).count()

    in_progress = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=current_worker.id),
        ProductionJob.status == "in_progress"
    ).count()

    completed_today = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=current_worker.id),
        ProductionJob.status == "completed",
        func.date(ProductionJob.end_time) == today
    ).count()

    # 3. Fetch today's punch summary details
    today_record = db.query(Attendance).filter(
        Attendance.worker_id == current_worker.id,
        Attendance.date == today
    ).first()

    today_punch_in = "--"
    today_punch_out = "--"
    today_working_hours = "--"
    today_ot_hours = "--"

    if today_record:
        if today_record.punch_in:
            # Treat naive database time as IST
            p_in = today_record.punch_in.replace(tzinfo=ist_offset) if today_record.punch_in.tzinfo is None else today_record.punch_in.astimezone(ist_offset)
            today_punch_in = p_in.strftime("%I:%M %p")
        if today_record.punch_out:
            p_out = today_record.punch_out.replace(tzinfo=ist_offset) if today_record.punch_out.tzinfo is None else today_record.punch_out.astimezone(ist_offset)
            today_punch_out = p_out.strftime("%I:%M %p")
        if today_record.net_working_hours is not None:
            today_working_hours = f"{today_record.net_working_hours:.2f} hrs"
        if today_record.ot_hours is not None:
            today_ot_hours = f"{today_record.ot_hours:.2f} hrs"

    return WorkerDashboardStats(
        present_days=present_days,
        absent_days=absent_days,
        leave_days=leave_days,
        ot_hours=ot_hours,
        sunday_worked=sunday_worked,
        total_assigned_jobs=total_assigned,
        pending_jobs=pending,
        in_progress_jobs=in_progress,
        completed_today=completed_today,
        today_punch_in=today_punch_in,
        today_punch_out=today_punch_out,
        today_working_hours=today_working_hours,
        today_ot_hours=today_ot_hours
    )

@router.get("/jobs", response_model=List[WorkerJob])
def get_worker_jobs(
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    query = db.query(ProductionJob).filter(ProductionJob.workers.any(id=current_worker.id))
    if status_filter:
        if status_filter.lower() == "pending":
            query = query.filter(ProductionJob.status.in_(["not_started", "assigned"]))
        elif status_filter.lower() == "in_progress":
            query = query.filter(ProductionJob.status == "in_progress")
        elif status_filter.lower() == "completed":
            query = query.filter(ProductionJob.status == "completed")
            
    jobs = query.all()
    return jobs

@router.get("/jobs/{job_id}", response_model=WorkerJob)
def get_job_details(
    job_id: int,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/jobs/{job_id}/start", response_model=WorkerJob)
def start_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "in_progress"
    job.start_time = datetime.utcnow()
    db.commit()
    db.refresh(job)
    return job

@router.post("/jobs/{job_id}/pause", response_model=WorkerJob)
def pause_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "paused"
    db.commit()
    db.refresh(job)
    return job

@router.post("/jobs/{job_id}/resume", response_model=WorkerJob)
def resume_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "in_progress"
    db.commit()
    db.refresh(job)
    return job

@router.post("/jobs/{job_id}/complete", response_model=WorkerJob)
def complete_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "completed"
    job.end_time = datetime.utcnow()
    job.progress_percent = 100
    db.commit()
    db.refresh(job)
    return job

@router.post("/jobs/{job_id}/progress-photo", response_model=PhotoUploadResponse)
def upload_progress_photo(
    job_id: int,
    photo: UploadFile = File(...),
    remarks: Optional[str] = Form(None),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    # Mocking S3/local save, just store dummy URL
    photo_url = f"/static/uploads/{photo.filename}"
    job_photo = JobPhoto(
        job_id=job_id,
        photo_url=photo_url,
        photo_type="progress",
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        uploaded_by_id=current_worker.id,
        remarks=remarks
    )
    db.add(job_photo)
    db.commit()
    db.refresh(job_photo)
    return PhotoUploadResponse(message="Progress photo uploaded successfully", photo=job_photo)

@router.post("/jobs/{job_id}/completion-photo", response_model=PhotoUploadResponse)
def upload_completion_photo(
    job_id: int,
    photo: UploadFile = File(...),
    remarks: Optional[str] = Form(None),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    # Mocking save
    photo_url = f"/static/uploads/{photo.filename}"
    job_photo = JobPhoto(
        job_id=job_id,
        photo_url=photo_url,
        photo_type="completion",
        gps_lat=gps_lat,
        gps_lng=gps_lng,
        uploaded_by_id=current_worker.id,
        remarks=remarks
    )
    db.add(job_photo)
    db.commit()
    db.refresh(job_photo)
    return PhotoUploadResponse(message="Completion photo uploaded successfully", photo=job_photo)

@router.get("/performance", response_model=PerformanceStats)
def get_performance_stats(
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    return PerformanceStats(
        jobsCompleted=12,
        avgCompletionTimeHrs=4.5,
        attendancePercent=95.0,
        otHours=10.0,
        performanceScore=92,
        monthlyTrend="up"
    )
