from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from datetime import datetime
from typing import Optional
from app.models.dispatch import DispatchRecord
from app.models.vehicle import Vehicle

def ensure_dispatch_record_for_vehicle(db: Session, vehicle: Vehicle) -> Optional[DispatchRecord]:
    if not vehicle:
        return None
    
    stage_lower = (vehicle.current_stage or "").lower().strip()
    is_dispatched_stage = stage_lower in ["dispatch", "dispatched", "delivered", "rtd", "ready_to_dispatch", "readytodispatch"] or bool(vehicle.dispatch_date_time)
    
    existing_dispatches = db.query(DispatchRecord).filter(DispatchRecord.vehicle_id == vehicle.id).order_by(DispatchRecord.id.asc()).all()
    if existing_dispatches:
        if len(existing_dispatches) > 1:
            for extra in existing_dispatches[1:]:
                db.delete(extra)
            db.commit()
        existing_dispatch = existing_dispatches[0]
        updated = False
        new_carrier = vehicle.transport_company or vehicle.driver_name or "Self Transport"
        if new_carrier and existing_dispatch.carrier != new_carrier:
            existing_dispatch.carrier = new_carrier
            updated = True
            
        new_destination = vehicle.dealer_name or vehicle.oem_name or "Factory Outbound"
        if new_destination and existing_dispatch.destination != new_destination:
            existing_dispatch.destination = new_destination
            updated = True
            
        if vehicle.dispatch_date_time and existing_dispatch.scheduled_date != vehicle.dispatch_date_time:
            existing_dispatch.scheduled_date = vehicle.dispatch_date_time
            updated = True

        if vehicle.lr_number and existing_dispatch.tracking_number != vehicle.lr_number:
            existing_dispatch.tracking_number = vehicle.lr_number
            updated = True

        if stage_lower in ["dispatched", "dispatch", "delivered"] and existing_dispatch.status != "dispatched":
            existing_dispatch.status = "dispatched"
            updated = True
        elif stage_lower in ["rtd", "ready_to_dispatch", "readytodispatch"] and existing_dispatch.status == "pending":
            existing_dispatch.status = "scheduled"
            updated = True

        if updated:
            db.commit()
            db.refresh(existing_dispatch)
        return existing_dispatch

    # Only create a brand new dispatch record if the vehicle is genuinely in a dispatch stage or has dispatch date
    if not is_dispatched_stage:
        return None

    carrier = vehicle.transport_company or vehicle.driver_name or "Self Transport"
    destination = vehicle.dealer_name or vehicle.oem_name or "Factory Outbound"
    tracking = vehicle.lr_number or (vehicle.tracking_id if str(vehicle.tracking_id).startswith("TRK-") else f"TRK-{vehicle.tracking_id or vehicle.id}")
    
    if stage_lower in ["dispatched", "dispatch", "delivered"]:
        init_status = "dispatched"
    elif stage_lower in ["rtd", "ready_to_dispatch", "readytodispatch"]:
        init_status = "scheduled"
    else:
        init_status = "pending"

    new_dispatch = DispatchRecord(
        vehicle_id=vehicle.id,
        scheduled_date=vehicle.dispatch_date_time or vehicle.submitted_at or datetime.now(),
        carrier=carrier,
        status=init_status,
        destination=destination,
        tracking_number=tracking
    )
    db.add(new_dispatch)
    db.commit()
    db.refresh(new_dispatch)
    return new_dispatch

def sync_dispatched_vehicles(db: Session):
    dispatch_stages = ["dispatch", "dispatched", "delivered", "rtd", "ready_to_dispatch", "readytodispatch"]
    vehicles = db.query(Vehicle).filter(
        or_(
            func.lower(Vehicle.current_stage).in_(dispatch_stages),
            Vehicle.dispatch_date_time != None
        )
    ).all()
    for v in vehicles:
        ensure_dispatch_record_for_vehicle(db, v)

    # Reverse sync: Any vehicle with a dispatched/delivered DispatchRecord must have current_stage in sync
    dispatched_records = db.query(DispatchRecord).filter(
        func.lower(DispatchRecord.status).in_(["dispatched", "delivered"])
    ).all()
    for d in dispatched_records:
        if d.vehicle:
            v_stage = (d.vehicle.current_stage or "").lower().strip()
            target_stage = "delivered" if d.status.lower() == "delivered" else "dispatch"
            if v_stage not in ["dispatch", "dispatched", "delivered"]:
                d.vehicle.current_stage = target_stage
                d.vehicle.progress_percent = 100
                if not d.vehicle.dispatch_date_time and d.scheduled_date:
                    d.vehicle.dispatch_date_time = d.scheduled_date
                db.add(d.vehicle)
    db.commit()


