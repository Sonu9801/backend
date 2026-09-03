from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models.dispatch import DispatchRecord
from app.schemas.dispatch import DispatchRecordCreate, DispatchRecordResponse
from app.services.websocket_manager import manager

router = APIRouter(prefix="/dispatch", tags=["dispatch"], dependencies=[Depends(get_current_active_user)])

from app.services.dispatch_service import sync_dispatched_vehicles

@router.get("")
def get_dispatch_records(
    page: int = 1,
    page_size: int = 10,
    search: Optional[str] = None,
    month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    from sqlalchemy import or_, extract
    from app.models.vehicle import Vehicle
    
    # Auto sync any vehicles in dispatch/dispatched/delivered/rtd stage
    sync_dispatched_vehicles(db)

    query = db.query(DispatchRecord)
    
    if search:
        query = query.join(Vehicle, DispatchRecord.vehicle_id == Vehicle.id).filter(
            or_(
                Vehicle.vehicle_number.ilike(f"%{search}%"),
                Vehicle.chassis_number.ilike(f"%{search}%"),
                Vehicle.tracking_id.ilike(f"%{search}%"),
                Vehicle.oem_name.ilike(f"%{search}%"),
                DispatchRecord.destination.ilike(f"%{search}%"),
                DispatchRecord.carrier.ilike(f"%{search}%"),
                DispatchRecord.status.ilike(f"%{search}%"),
            )
        )
        
    if month:
        try:
            parts = month.split("-")
            if len(parts) == 2:
                year, m = int(parts[0]), int(parts[1])
                query = query.filter(
                    extract('year', DispatchRecord.scheduled_date) == year,
                    extract('month', DispatchRecord.scheduled_date) == m
                )
        except Exception:
            pass

    from datetime import datetime
    if start_date:
        try:
            if len(start_date) == 10:
                sd = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                sd = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            query = query.filter(DispatchRecord.scheduled_date >= sd)
        except Exception:
            pass

    if end_date:
        try:
            if len(end_date) == 10:
                ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            else:
                ed = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            query = query.filter(DispatchRecord.scheduled_date <= ed)
        except Exception:
            pass

    total = query.count()
    total_pages = max(1, -(-total // page_size))
    offset = (page - 1) * page_size
    items = query.order_by(DispatchRecord.scheduled_date.desc()).offset(offset).limit(page_size).all()

    result_items = []
    for record in items:
        rec_dict = DispatchRecordResponse.model_validate(record).model_dump()
        if record.vehicle:
            v = record.vehicle
            rec_dict["vehicleNumber"] = v.vehicle_number
            rec_dict["chassisNumber"] = v.chassis_number or v.vin or f"CH-{v.id}"
            rec_dict["oemName"] = v.oem_name
            rec_dict["vehicleModel"] = v.vehicle_model
            rec_dict["productCategory"] = v.product_category
            rec_dict["vin"] = v.vin
            rec_dict["driverName"] = v.driver_name
            rec_dict["driverPhone"] = v.driver_mobile_number
            rec_dict["truckNumber"] = v.truck_number
            rec_dict["lrNumber"] = v.lr_number
            rec_dict["invoiceNumber"] = v.invoice_number
            rec_dict["dispatchChallanNumber"] = v.dispatch_challan_number
            rec_dict["trackingId"] = v.tracking_id or f"TRK-{v.id}"

            # Fallbacks
            rec_dict["vehicle_number"] = v.vehicle_number
            rec_dict["chassis_number"] = v.chassis_number or v.vin
            rec_dict["oem_name"] = v.oem_name
        result_items.append(rec_dict)

    return {
        "items": result_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

@router.post("", response_model=DispatchRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_dispatch_record(dispatch_in: DispatchRecordCreate, db: Session = Depends(get_db)):
    dispatch_record = DispatchRecord(**dispatch_in.model_dump())
    db.add(dispatch_record)
    db.commit()
    db.refresh(dispatch_record)
    
    # Broadcast change
    response_data = DispatchRecordResponse.model_validate(dispatch_record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_RECORD_CREATED",
        "data": response_data
    })
    return dispatch_record

@router.patch("/{record_id}/status", response_model=DispatchRecordResponse)
async def update_dispatch_status(record_id: int, status: str, db: Session = Depends(get_db)):
    record = db.query(DispatchRecord).filter(DispatchRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
    record.status = status
    
    if status.lower() == "delayed":
        from app.models.notification import Notification
        notification = Notification(
            type="warning",
            title="Dispatch Delayed",
            message=f"Dispatch for vehicle {record.vehicle_id} has been delayed.",
            module="dispatch",
            reference_id=str(record.id),
            target_url="/dispatch",
        )
        db.add(notification)

    db.commit()
    db.refresh(record)
    
    if status.lower() == "delayed":
        try:
            await manager.broadcast({"type": "NEW_NOTIFICATION"})
        except Exception:
            pass
    
    # Broadcast status update
    response_data = DispatchRecordResponse.model_validate(record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_STATUS_CHANGED",
        "data": response_data
    })
    return record

from app.schemas.dispatch import DispatchRecordUpdate
from datetime import datetime

@router.put("/{record_id}", response_model=DispatchRecordResponse)
async def update_dispatch_record(record_id: int, update_in: DispatchRecordUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_active_user)):
    record = db.query(DispatchRecord).filter(DispatchRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
        
    old_data = DispatchRecordResponse.model_validate(record).model_dump()
    update_data = update_in.model_dump(exclude_unset=True)
    reason = update_data.pop("reason", "No reason provided")
    
    v_fields = {
        "chassis_number": update_data.pop("chassis_number", None),
        "vehicle_number": update_data.pop("vehicle_number", None),
        "oem_name": update_data.pop("oem_name", None),
        "driver_name": update_data.pop("driver_name", None),
        "driver_mobile_number": update_data.pop("driver_phone", None),
        "truck_number": update_data.pop("truck_number", None),
        "lr_number": update_data.pop("lr_number", None),
        "invoice_number": update_data.pop("invoice_number", None),
        "dispatch_challan_number": update_data.pop("dispatch_challan_number", None),
        "tracking_id": update_data.pop("tracking_id", None),
        "dispatch_date_time": update_data.get("scheduled_date"),
    }

    was_delivered = record.status.lower() != "delivered"
    for key, value in update_data.items():
        setattr(record, key, value)

    if record.vehicle:
        v = record.vehicle
        for vk, vv in v_fields.items():
            if vv is not None:
                setattr(v, vk, vv)
        db.add(v)
        
    is_delivered = record.status.lower() == "delivered"
    
    if was_delivered and is_delivered:
        if not record.delivered_time:
            record.delivered_time = datetime.now()
            
        from app.models.notification import Notification
        notification = Notification(
            type="success",
            title="Delivery Completed",
            message=f"Vehicle {record.vehicle_id} has been delivered successfully.",
            module="oem-portal",
            reference_id=str(record.id),
            target_url="/oem-portal",
        )
        db.add(notification)
        
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

    db.commit()
    db.refresh(record)
    
    new_data = DispatchRecordResponse.model_validate(record).model_dump()
    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "dispatch_record_updated", f"Dispatch Record #{record.id} updated",
        edited_by=getattr(current_user, "username", "System"),
        reason=reason, old_value=old_data, new_value=new_data
    )
    
    response_data = DispatchRecordResponse.model_validate(record).model_dump()
    await manager.broadcast({
        "type": "DISPATCH_RECORD_UPDATED",
        "data": response_data
    })
    return record

@router.delete("/{record_id}", status_code=status.HTTP_200_OK)
async def delete_dispatch_record(
    record_id: int,
    delete_vehicle: bool = False,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    record = db.query(DispatchRecord).filter(DispatchRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Dispatch record not found")
        
    old_data = DispatchRecordResponse.model_validate(record).model_dump()
    vehicle = record.vehicle
    
    if vehicle:
        if delete_vehicle:
            db.delete(vehicle)
        else:
            # Change vehicle stage out of dispatch list so auto-sync won't recreate this record
            vehicle.current_stage = "received"
            vehicle.dispatch_date_time = None
            db.add(vehicle)

    # Delete all dispatch records associated with this vehicle_id
    db.query(DispatchRecord).filter(DispatchRecord.vehicle_id == record.vehicle_id).delete()
    db.commit()

    from app.services.audit import log_audit_event
    await log_audit_event(
        db, "dispatch_record_deleted", f"Dispatch Record #{record_id} deleted permanently",
        edited_by=getattr(current_user, "username", "System"),
        reason="Administrative deletion", old_value=old_data, new_value=None
    )
    
    await manager.broadcast({
        "type": "DISPATCH_RECORD_DELETED",
        "data": {"id": record_id}
    })
    return {"message": "Dispatch record deleted permanently", "id": record_id}
