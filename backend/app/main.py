import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, workers, worker, vehicles, quality, dispatch, activities, websocket, attendance, payroll, oem_schedule, attendance_settings, factory_settings, notifications, jobs, invoices, revenue, leave, documents, team, components
from app.models.component_task import ComponentTask

# Create database tables if they do not exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FOXFLOW ERP API",
    description="Backend API for FoxFlow ERP Manufacturing Execution System",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local uploads static files
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include Routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(workers.router, prefix="/api")
app.include_router(vehicles.router, prefix="/api")
app.include_router(activities.router, prefix="/api")
app.include_router(oem_schedule.router, prefix="/api")
app.include_router(quality.router, prefix="/api")
app.include_router(dispatch.router, prefix="/api")
app.include_router(invoices.router, prefix="/api")
app.include_router(revenue.router, prefix="/api")
app.include_router(attendance.router, prefix="/api")
app.include_router(attendance_settings.router, prefix="/api")
app.include_router(factory_settings.router, prefix="/api")
app.include_router(payroll.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(leave.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(team.router, prefix="/api")
app.include_router(worker.router, prefix="/api")
app.include_router(components.router, prefix="/api")
app.include_router(websocket.router, prefix="")

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "FOXFLOW ERP API is healthy"}

import asyncio
from app.tasks.cleanup import cleanup_old_attendance_photos

@app.on_event("startup")
async def startup_event():
    # Start the background task to delete old attendance photos (older than 60 days)
    asyncio.create_task(cleanup_old_attendance_photos())
