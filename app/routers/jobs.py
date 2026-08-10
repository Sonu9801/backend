from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date
from typing import List

from app.database import get_db
from app.models.production_job import ProductionJob
from app.models.vehicle import Vehicle
from app.models.user import User
from app.models.notification import Notification
from app.schemas.production_job import ProductionJobCreate, ProductionJobUpdate, ProductionJobResponse
from app.auth import get_current_active_user
from app.services.websocket_manager import manager

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("/assign", response_model=ProductionJobResponse)
async def assign_job(payload: ProductionJobCreate, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == payload.vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    job = ProductionJob(
        vehicle_id=payload.vehicle_id,
        stage=payload.stage,
        status="assigned",
        supervisor_id=payload.supervisor_id or current_user.id,
        expected_duration_minutes=payload.expected_duration_minutes,
        assignment_source=payload.assignment_source
    )
    
    workers = db.query(User).filter(User.id.in_(payload.worker_ids)).all()
    if len(workers) != len(payload.worker_ids):
        raise HTTPException(status_code=404, detail="One or more workers not found")
        
    job.workers = workers
    db.add(job)
    
    # Notifications for workers
    for w in workers:
        notif = Notification(
            type="info",
            title="New Job Assigned",
            message=f"You have been assigned to vehicle {vehicle.vehicle_number} for stage {payload.stage}.",
            module="workforce",
            reference_id=str(w.id)
        )
        db.add(notif)
        
    db.commit()
    db.refresh(job)
    
    try:
        await manager.broadcast({"type": "NEW_NOTIFICATION"})
    except Exception:
        pass
    
    # Broadcast to update production board
    await manager.broadcast({
        "type": "JOB_ASSIGNED",
        "data": {
            "vehicleId": vehicle.id,
            "stage": payload.stage,
            "jobId": job.id
        }
    })
    
    return job

@router.get("/worker/{worker_id}/today", response_model=List[ProductionJobResponse])
def get_worker_today_jobs(worker_id: int, db: Session = Depends(get_db)):
    """Returns all of today's jobs for the worker including completed ones (for overview stats)."""
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    # Get active (non-completed) jobs assigned to worker
    active_jobs = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=worker_id),
        ProductionJob.status.notin_(["completed", "rejected"])
    ).all()

    # Get today's completed jobs
    completed_today = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=worker_id),
        ProductionJob.status == "completed",
        ProductionJob.end_time >= today_start,
        ProductionJob.end_time <= today_end
    ).all()

    # Merge, avoiding duplicates
    all_job_ids = {j.id for j in active_jobs}
    merged = list(active_jobs)
    for j in completed_today:
        if j.id not in all_job_ids:
            merged.append(j)
    return merged

@router.get("/worker/{worker_id}", response_model=List[ProductionJobResponse])
def get_worker_jobs(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    jobs = db.query(ProductionJob).filter(
        ProductionJob.workers.any(id=worker_id),
        ProductionJob.status.notin_(["completed", "rejected"])
    ).all()
    return jobs

@router.get("/worker/{worker_id}/history", response_model=List[ProductionJobResponse])
def get_worker_job_history(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
        
    jobs = db.query(ProductionJob).options(
        joinedload(ProductionJob.photos)
    ).filter(
        ProductionJob.workers.any(id=worker_id),
        ProductionJob.status == "completed"
    ).order_by(ProductionJob.end_time.desc()).all()
    return jobs

@router.patch("/{job_id}/status", response_model=ProductionJobResponse)
async def update_job_status(job_id: int, payload: ProductionJobUpdate, db: Session = Depends(get_db)):
    job = db.query(ProductionJob).filter(ProductionJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if payload.status:
        job.status = payload.status
        if payload.status == "in_progress" and not job.start_time:
            job.start_time = datetime.now()
        elif payload.status == "completed":
            job.end_time = datetime.now()
            # If completing, auto-handoff to QC
            vehicle = job.vehicle
            old_stage = vehicle.current_stage
            vehicle.current_stage = "quality"
            vehicle.progress_percent = 0
            
            await manager.broadcast({
                "type": "VEHICLE_STAGE_CHANGED",
                "data": {
                    "vehicleId": vehicle.id,
                    "oldStage": old_stage,
                    "newStage": "quality",
                    "progressPercent": 0,
                    "vehicle": {}
                }
            })
            
    if payload.photo_proof_url:
        job.photo_proof_url = payload.photo_proof_url
    if payload.comments:
        job.comments = payload.comments
        
    db.commit()
    db.refresh(job)
    
    await manager.broadcast({
        "type": "JOB_STATUS_CHANGED",
        "data": {
            "jobId": job.id,
            "status": job.status,
            "vehicleId": job.vehicle_id
        }
    })
    
    return job
