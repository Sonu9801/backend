from sqlalchemy.orm import Session
from datetime import datetime
import json
from typing import Optional, Any
from app.models.activity import ActivityEvent
from app.services.websocket_manager import manager
from app.schemas.activity import ActivityEventResponse

def default_json_serializer(obj: Any) -> str:
    """Helper for JSON serialization of datetimes etc."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

async def log_audit_event(
    db: Session,
    event_type: str,
    description: str,
    edited_by: str,
    reason: str,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    vehicle_id: Optional[int] = None,
    worker_id: Optional[int] = None
) -> ActivityEvent:
    old_val_str = json.dumps(old_value, default=default_json_serializer) if old_value is not None else None
    new_val_str = json.dumps(new_value, default=default_json_serializer) if new_value is not None else None

    event = ActivityEvent(
        event_type=event_type,
        description=description,
        vehicle_id=vehicle_id,
        worker_id=worker_id,
        timestamp=datetime.utcnow(),
        old_value=old_val_str,
        new_value=new_val_str,
        edited_by=edited_by,
        reason=reason
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Broadcast via websockets
    response_data = ActivityEventResponse.model_validate(event).model_dump()
    # Pydantic may leave datetimes as objects in dump for some versions, convert them:
    if isinstance(response_data.get('timestamp'), datetime):
        response_data['timestamp'] = response_data['timestamp'].isoformat()
        
    await manager.broadcast({
        "type": "ACTIVITY_EVENT_CREATED",
        "data": response_data
    })
    
    return event
