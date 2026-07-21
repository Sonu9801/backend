from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.auth import get_current_user, get_current_active_user
from app.models.component_task import ComponentTask
from app.models.user import User
from app.schemas.component_task import ComponentTaskCreate, ComponentTaskResponse, ComponentTaskSubmit

router = APIRouter(prefix="/components", tags=["components"], dependencies=[Depends(get_current_user)])

@router.post("/start", response_model=ComponentTaskResponse)
def start_component_task(task_in: ComponentTaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Find if this component is already in progress
    task = db.query(ComponentTask).filter(
        ComponentTask.component_number == task_in.component_number,
        ComponentTask.component_type == task_in.component_type,
        ComponentTask.status == "in_progress"
    ).first()

    if task:
        # Check if worker is already assigned
        if current_user in task.workers:
            raise HTTPException(status_code=400, detail="You are already assigned to this task.")
            
        # Check limit for Platform
        if task.component_type.lower() == "platform" and len(task.workers) >= 2:
            raise HTTPException(status_code=400, detail="Maximum 2 workers allowed for a Platform task.")
            
        task.workers.append(current_user)
        db.commit()
        db.refresh(task)
        return task
    else:
        # Create new task
        new_task = ComponentTask(
            component_type=task_in.component_type,
            component_number=task_in.component_number,
        )
        new_task.workers.append(current_user)
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        return new_task

@router.post("/{task_id}/submit", response_model=ComponentTaskResponse)
def submit_component_task(task_id: int, submit_in: ComponentTaskSubmit, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(ComponentTask).filter(ComponentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if current_user not in task.workers:
        raise HTTPException(status_code=403, detail="You are not assigned to this task")
        
    task.photo_proof_url = submit_in.photo_proof_url
    task.notes = submit_in.notes
    task.status = "completed"
    task.end_time = datetime.utcnow()
    
    db.commit()
    db.refresh(task)
    return task

@router.get("/worker/{worker_id}", response_model=List[ComponentTaskResponse])
def get_worker_components(worker_id: int, db: Session = Depends(get_db)):
    worker = db.query(User).filter(User.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    return worker.component_tasks

@router.get("", response_model=List[ComponentTaskResponse])
def get_all_components(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return db.query(ComponentTask).order_by(ComponentTask.id.desc()).all()
