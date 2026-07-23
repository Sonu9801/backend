from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleResponse, VehicleUpdate
from app.services.websocket_manager import manager

router = APIRouter(prefix="/vehicles", tags=["vehicles"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=List[VehicleResponse])
def get_vehicles(db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    query = db.query(Vehicle)
    if current_user.role == "oem" and current_user.dealer_name:
        query = query.filter(Vehicle.oem_name.ilike(f"%{current_user.dealer_name}%"))
    return query.order_by(Vehicle.id).all()

@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):
    # Extract assigned worker IDs
    assigned_worker_ids = vehicle_in.assigned_worker_ids or []
    
    # Exclude assigned_worker_ids from the kwargs
    vehicle_data = vehicle_in.model_dump(exclude={"assigned_worker_ids"})
    vehicle = Vehicle(**vehicle_data)
    
    # Query and associate workers
    if assigned_worker_ids:
        workers = db.query(User).filter(User.id.in_(assigned_worker_ids)).all()
        vehicle.workers = workers
        
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    # Broadcast change
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_CREATED",
        "data": response_data
    })
    return vehicle

@router.post("/oem-dispatch", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_oem_dispatch(vehicle_in: VehicleCreate, db: Session = Depends(get_db)):
    # Extract assigned worker IDs
    assigned_worker_ids = vehicle_in.assigned_worker_ids or []
    
    # Exclude assigned_worker_ids from the kwargs
    vehicle_data = vehicle_in.model_dump(exclude={"assigned_worker_ids"})
    
    # FOR OEM DISPATCH: Always force status to 'oem'
    vehicle_data["current_stage"] = "oem"
    
    vehicle = Vehicle(**vehicle_data)
    
    # Query and associate workers
    if assigned_worker_ids:
        workers = db.query(User).filter(User.id.in_(assigned_worker_ids)).all()
        vehicle.workers = workers
        
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    
    # Create Notification
    from app.models.notification import Notification
    notification = Notification(
        type="warning",
        title="New OEM Vehicle Waiting For Verification",
        message=f"Vehicle {vehicle.tracking_id} submitted by {vehicle.oem_name} requires verification.",
        module="production",
        reference_id=str(vehicle.id),
        target_url=f"/production/verification/{vehicle.id}",
    )
    db.add(notification)
    db.commit()
    
    # Broadcast change
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_CREATED",
        "data": response_data
    })
    
    # Broadcast notification
    await manager.broadcast({
        "type": "NEW_NOTIFICATION",
        "data": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "target_url": notification.target_url
        }
    })
    
    return vehicle

@router.put("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(vehicle_id: int, vehicle_in: VehicleUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    old_data = VehicleResponse.model_validate(vehicle).model_dump()
    update_data = vehicle_in.model_dump(exclude_unset=True)
    assigned_worker_ids = update_data.pop("assigned_worker_ids", None)
    reason = update_data.pop("reason", "No reason provided")
    
    for key, value in update_data.items():
        setattr(vehicle, key, value)
        
    if assigned_worker_ids is not None:
        workers = db.query(User).filter(User.id.in_(assigned_worker_ids)).all()
        vehicle.workers = workers
        
    db.commit()
    db.refresh(vehicle)
    
    new_data = VehicleResponse.model_validate(vehicle).model_dump()
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "vehicle_updated", f"Vehicle {vehicle.tracking_id} updated",
        edited_by=getattr(current_user, "email", "System"),
        reason=reason, old_value=old_data, new_value=new_data, vehicle_id=vehicle.id
    )
    
    # Broadcast change
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_UPDATED",
        "data": response_data
    })
    return vehicle

from fastapi import APIRouter, Depends, HTTPException, status, Body

@router.patch("/{vehicle_id}/stage", response_model=VehicleResponse)
async def update_vehicle_stage(
    vehicle_id: int, 
    stage: str = Body(...), 
    progress: Optional[int] = Body(None),
    priority: Optional[str] = Body(None),
    reason: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    old_data = VehicleResponse.model_validate(vehicle).model_dump()
    old_stage = vehicle.current_stage
    vehicle.current_stage = stage
    if priority:
        vehicle.priority = priority
    if progress is not None:
        vehicle.progress_percent = progress
    elif stage == "Received":
        vehicle.progress_percent = 0
    elif stage == "Fabrication":
        vehicle.progress_percent = 30
    elif stage == "Paint":
        vehicle.progress_percent = 65
    elif stage == "ReadyToDispatch" or stage == "RTD":
        vehicle.progress_percent = 100
    elif stage == "Dispatched" or stage == "dispatch":
        vehicle.progress_percent = 100
        from app.models.dispatch import DispatchRecord
        from datetime import datetime
        existing_dispatch = db.query(DispatchRecord).filter(DispatchRecord.vehicle_id == vehicle.id).first()
        if not existing_dispatch:
            new_dispatch = DispatchRecord(
                vehicle_id=vehicle.id,
                scheduled_date=datetime.now(),
                carrier="Pending Assignment",
                status="pending",
                destination="Pending Destination",
                tracking_number=f"TRK-{vehicle.tracking_id}"
            )
            db.add(new_dispatch)
        
    db.commit()
    db.refresh(vehicle)
    
    new_data = VehicleResponse.model_validate(vehicle).model_dump()
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "vehicle_stage_updated", f"Vehicle {vehicle.tracking_id} stage changed from {old_stage} to {stage}",
        edited_by=getattr(current_user, "name", "System"),
        reason=reason or "Stage Update", old_value=old_data, new_value=new_data, vehicle_id=vehicle.id
    )
    
    # Broadcast stage change
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_STAGE_CHANGED",
        "data": {
            "vehicleId": vehicle.id,
            "oldStage": old_stage,
            "newStage": vehicle.current_stage,
            "progressPercent": vehicle.progress_percent,
            "vehicle": response_data
        }
    })
    return vehicle

from pydantic import BaseModel
from datetime import datetime

class RejectPayload(BaseModel):
    reason: str

class VerifyPayload(BaseModel):
    action: str # "approve", "reject", "hold"
    remarks: str
    expected_resolution: Optional[str] = None
    platform_number: Optional[str] = None
    chassis_number: Optional[str] = None
    vin: Optional[str] = None
    driver_name: Optional[str] = None
    driver_mobile_number: Optional[str] = None
    truck_number: Optional[str] = None
    arrival_photos: Optional[str] = None

@router.post("/{vehicle_id}/verify", response_model=VehicleResponse)
async def verify_vehicle(vehicle_id: int, payload: VerifyPayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    if current_user.role not in ["supervisor", "manager", "admin", "owner"]:
        raise HTTPException(status_code=403, detail="Not authorized to verify vehicles")
        
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    old_stage = vehicle.current_stage
    from app.models.notification import Notification
    
    if payload.action == "approve":
        vehicle.current_stage = "received"
        vehicle.verification_status = "approved"
        vehicle.verified_at = datetime.now()
        vehicle.gate_entry_time = datetime.now()
        vehicle.verified_by = getattr(current_user, "name", "System")
        vehicle.progress_percent = 0
        vehicle.verification_notes = payload.remarks
        
        # Generate gate entry number (e.g., GE-YYYYMMDD-ID)
        date_str = datetime.now().strftime("%Y%m%d")
        vehicle.gate_entry_number = f"GE-{date_str}-{vehicle.id:04d}"
        
        notification_type = "success"
        notification_title = "Vehicle Verified & Accepted"
        notification_message = f"Vehicle {vehicle.tracking_id} has been accepted into Production. Gate Entry: {vehicle.gate_entry_number}"
        
    elif payload.action == "reject":
        # Vehicle goes back to OEM stage but marked as rejected
        vehicle.current_stage = "oem"
        vehicle.verification_status = "rejected"
        vehicle.rejection_reason = payload.remarks
        
        notification_type = "error"
        notification_title = "Vehicle Dispatch Rejected"
        notification_message = f"Vehicle {vehicle.tracking_id} was rejected at Gate Entry. Reason: {payload.remarks}"
        
    elif payload.action == "hold":
        vehicle.verification_status = "hold"
        vehicle.hold_reason = payload.remarks
        vehicle.expected_resolution = payload.expected_resolution
        
        notification_type = "warning"
        notification_title = "Vehicle On Hold"
        notification_message = f"Vehicle {vehicle.tracking_id} placed on hold at Gate Entry. Reason: {payload.remarks}"
        
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    # Update verification fields if provided
    if payload.platform_number: vehicle.platform_number = payload.platform_number
    if payload.chassis_number: vehicle.chassis_number = payload.chassis_number
    if payload.vin: vehicle.vin = payload.vin
    if payload.driver_name: vehicle.driver_name = payload.driver_name
    if payload.driver_mobile_number: vehicle.driver_mobile_number = payload.driver_mobile_number
    if payload.truck_number: vehicle.truck_number = payload.truck_number
    if payload.arrival_photos: vehicle.arrival_photos = payload.arrival_photos
    
    db.commit()
    db.refresh(vehicle)
    
    # Create Notification
    notification = Notification(
        type=notification_type,
        title=notification_title,
        message=notification_message,
        module="production",
        reference_id=str(vehicle.id),
        target_url=f"/production?tab=incoming",
    )
    db.add(notification)
    db.commit()
    
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_STAGE_CHANGED",
        "data": {
            "vehicleId": vehicle.id,
            "oldStage": old_stage,
            "newStage": vehicle.current_stage,
            "progressPercent": vehicle.progress_percent,
            "vehicle": response_data
        }
    })
    
    await manager.broadcast({
        "type": "NEW_NOTIFICATION",
        "data": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "target_url": notification.target_url
        }
    })
    return vehicle

@router.post("/{vehicle_id}/reject", response_model=VehicleResponse)
async def reject_vehicle(vehicle_id: int, payload: RejectPayload, db: Session = Depends(get_db)):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    old_stage = vehicle.current_stage
    vehicle.current_stage = "rejected"
    vehicle.verification_status = "rejected"
    vehicle.rejection_reason = payload.reason
    
    db.commit()
    db.refresh(vehicle)
    
    # Create Notification for rejection
    from app.models.notification import Notification
    notification = Notification(
        type="error",
        title="Vehicle Dispatch Rejected",
        message=f"Vehicle {vehicle.tracking_id} was rejected. Reason: {payload.reason}",
        module="oem-portal",
        reference_id=str(vehicle.id),
        target_url="/oem-portal",
    )
    db.add(notification)
    db.commit()
    
    response_data = VehicleResponse.model_validate(vehicle).model_dump()
    await manager.broadcast({
        "type": "VEHICLE_STAGE_CHANGED",
        "data": {
            "vehicleId": vehicle.id,
            "oldStage": old_stage,
            "newStage": vehicle.current_stage,
            "progressPercent": vehicle.progress_percent,
            "vehicle": response_data
        }
    })
    
    await manager.broadcast({
        "type": "NEW_NOTIFICATION",
        "data": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "target_url": notification.target_url
        }
    })
    return vehicle
