from fastapi import APIRouter, Depends
from app.auth import get_current_active_user
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.factory_settings import FactorySettings
from app.schemas.factory_settings import FactorySettingsUpdate, FactorySettingsResponse

router = APIRouter(prefix="/settings/factory", tags=["settings"], dependencies=[Depends(get_current_active_user)])

@router.get("", response_model=FactorySettingsResponse)
def get_factory_settings(db: Session = Depends(get_db)):
    settings = db.query(FactorySettings).first()
    if not settings:
        settings = FactorySettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

@router.put("", response_model=FactorySettingsResponse)
def update_factory_settings(settings_in: FactorySettingsUpdate, db: Session = Depends(get_db)):
    settings = db.query(FactorySettings).first()
    if not settings:
        settings = FactorySettings()
        db.add(settings)
    
    for key, value in settings_in.model_dump().items():
        setattr(settings, key, value)
    
    db.commit()
    db.refresh(settings)
    return settings
