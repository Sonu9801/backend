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

        if stage_lower in ["dispatched", "delivered"] and existing_dispatch.status != "dispatched":
            existing_dispatch.status = "dispatched"
            updated = True
        elif stage_lower in ["dispatch", "rtd"] and existing_dispatch.status == "pending":
            existing_dispatch.status = "scheduled"
            updated = True

        if updated:
            db.commit()
            db.refresh(existing_dispatch)
        return existing_dispatch

    carrier = vehicle.transport_company or vehicle.driver_name or "Self Transport"
    destination = vehicle.dealer_name or vehicle.oem_name or "Factory Outbound"
    tracking = f"TRK-{vehicle.tracking_id or vehicle.id}"
    
    if stage_lower in ["dispatched", "delivered"]:
        init_status = "dispatched"
    elif stage_lower in ["dispatch", "rtd"]:
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
    all_vehicles = db.query(Vehicle).all()
    for v in all_vehicles:
        ensure_dispatch_record_for_vehicle(db, v)

