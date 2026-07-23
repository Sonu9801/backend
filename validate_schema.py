import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from app.database import engine, get_db, Base

# Import all models to ensure they are registered in Base.metadata
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.production_job import ProductionJob
from app.models.quality import QCRecord, DefectRecord
from app.models.dispatch import DispatchRecord
from app.models.invoice import Invoice
from app.models.attendance import AttendanceLog, AttendanceException
from app.models.salary_profile import SalaryProfile
from app.models.leave import LeaveRequest
from app.models.notification import Notification

def validate():
    print("Validating Database Schema...")
    inspector = inspect(engine)
    db_tables = inspector.get_table_names()
    model_tables = Base.metadata.tables.keys()
    
    missing_tables = set(model_tables) - set(db_tables)
    if missing_tables:
        print(f"Missing tables in DB: {missing_tables}")
    else:
        print("All model tables exist in DB.")
        
    all_good = True
    for table_name in model_tables:
        if table_name in db_tables:
            db_columns = {col['name'] for col in inspector.get_columns(table_name)}
            model_columns = {col.name for col in Base.metadata.tables[table_name].columns}
            missing_cols = model_columns - db_columns
            if missing_cols:
                all_good = False
                print(f"Table '{table_name}' is missing columns: {missing_cols}")
                
    if all_good:
        print("All model columns exist in the DB schema!")

if __name__ == "__main__":
    validate()
