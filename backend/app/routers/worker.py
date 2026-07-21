from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

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
# Assuming a get_current_active_user dependency exists, if not using a mock for now
# from app.dependencies import get_current_active_user

router = APIRouter(prefix="/worker", tags=["Worker PWA"])

# Mock dependency for worker auth
def get_current_worker(db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.role == "Worker").first()
    if not worker:
        # Create a dummy worker if none exist for testing
        worker = User(email="worker@test.com", name="Test Worker", role="Worker")
        db.add(worker)
        db.commit()
        db.refresh(worker)
    return worker

@router.get("/dashboard", response_model=WorkerDashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_worker: User = Depends(get_current_worker)
):
    # Dummy logic to return stats for the dashboard
    return WorkerDashboardStats(
        presentDays=20,
        absentDays=1,
        leaveDays=2,
        otHours=15.5,
        sundayWorked=1,
        totalAssignedJobs=10,
        pendingJobs=3,
        inProgressJobs=2,
        completedToday=1
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
