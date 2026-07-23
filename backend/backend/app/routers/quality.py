from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.quality import QCRecord, DefectRecord
from app.schemas.quality import QCRecordCreate, QCRecordResponse, QCRecordUpdate, DefectRecordCreate, DefectRecordResponse
from app.services.websocket_manager import manager
import os
import uuid
from app.config import settings

router = APIRouter(prefix="/quality", tags=["quality"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=List[QCRecordResponse])
def get_qc_records(db: Session = Depends(get_db)):
    return db.query(QCRecord).order_by(QCRecord.id.desc()).all()

@router.post("", response_model=QCRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_qc_record(qc_in: QCRecordCreate, db: Session = Depends(get_db)):
    qc_record = QCRecord(**qc_in.model_dump())
    db.add(qc_record)
    db.commit()
    db.refresh(qc_record)
    
    # Broadcast change
    response_data = QCRecordResponse.model_validate(qc_record).model_dump()
    await manager.broadcast({
        "type": "QC_RECORD_CREATED",
        "data": response_data
    })
    return qc_record

@router.get("/{qc_id}", response_model=QCRecordResponse)
def get_qc_record(qc_id: int, db: Session = Depends(get_db)):
    qc_record = db.query(QCRecord).filter(QCRecord.id == qc_id).first()
    if not qc_record:
        raise HTTPException(status_code=404, detail="QC record not found")
    return qc_record

@router.put("/{qc_id}", response_model=QCRecordResponse)
async def update_qc_record(qc_id: int, qc_in: QCRecordUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    qc_record = db.query(QCRecord).filter(QCRecord.id == qc_id).first()
    if not qc_record:
        raise HTTPException(status_code=404, detail="QC record not found")
        
    old_data = QCRecordResponse.model_validate(qc_record).model_dump()
    update_data = qc_in.model_dump(exclude_unset=True)
    reason = update_data.pop("reason", "No reason provided")
    
    for key, value in update_data.items():
        setattr(qc_record, key, value)
        
    db.commit()
    db.refresh(qc_record)
    
    new_data = QCRecordResponse.model_validate(qc_record).model_dump()
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "qc_record_updated", f"QC Record #{qc_record.id} updated",
        edited_by=getattr(current_user, "username", "System"),
        reason=reason, old_value=old_data, new_value=new_data
    )
    
    response_data = QCRecordResponse.model_validate(qc_record).model_dump()
    await manager.broadcast({
        "type": "QC_RECORD_UPDATED",
        "data": response_data
    })
    return qc_record

@router.post("/{qc_id}/photos", response_model=QCRecordResponse)
async def upload_qc_photo(qc_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    qc_record = db.query(QCRecord).filter(QCRecord.id == qc_id).first()
    if not qc_record:
        raise HTTPException(status_code=404, detail="QC record not found")

    file_extension = os.path.splitext(file.filename)[1]
    filename = f"qc_{qc_id}_{uuid.uuid4().hex}{file_extension}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    photo_url = f"/uploads/{filename}"
    
    # Update photos array
    current_photos = qc_record.photos or []
    current_photos.append(photo_url)
    
    # Need to reassign to trigger SQLAlchemy JSON detection
    qc_record.photos = list(current_photos)
    
    db.commit()
    db.refresh(qc_record)
    
    response_data = QCRecordResponse.model_validate(qc_record).model_dump()
    await manager.broadcast({
        "type": "QC_RECORD_UPDATED",
        "data": response_data
    })
    
    return qc_record

@router.get("/defects/all", response_model=List[DefectRecordResponse])
def get_all_defects(db: Session = Depends(get_db)):
    return db.query(DefectRecord).order_by(DefectRecord.id.desc()).all()

@router.post("/defects", response_model=DefectRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_defect(defect_in: DefectRecordCreate, db: Session = Depends(get_db)):
    defect = DefectRecord(**defect_in.model_dump())
    db.add(defect)
    
    # Update QC Record to ensure it has a Failed or Rework status when defect is logged? 
    # Not strictly required here, client can update the QC Record status separately.
    
    db.commit()
    db.refresh(defect)
    
    response_data = DefectRecordResponse.model_validate(defect).model_dump()
    await manager.broadcast({
        "type": "DEFECT_CREATED",
        "data": response_data
    })
    return defect

@router.put("/defects/{defect_id}/status", response_model=DefectRecordResponse)
async def update_defect_status(defect_id: int, status_str: str, db: Session = Depends(get_db)):
    defect = db.query(DefectRecord).filter(DefectRecord.id == defect_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect not found")
        
    defect.status = status_str
    db.commit()
    db.refresh(defect)
    
    response_data = DefectRecordResponse.model_validate(defect).model_dump()
    await manager.broadcast({
        "type": "DEFECT_UPDATED",
        "data": response_data
    })
    return defect
