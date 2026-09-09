import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import engine, Base, init_db
from app.routers import auth, users, workers, worker, vehicles, quality, dispatch, activities, websocket, attendance, payroll, oem_schedule, attendance_settings, factory_settings, notifications, jobs, invoices, revenue, leave, documents, team, components, performance
from app.models.component_task import ComponentTask
from app.models.performance import WorkerDailyPerformance, TeamDailySummary

app = FastAPI(
    title="FOXFLOW ERP API",
    description="Backend API for FoxFlow ERP Manufacturing Execution System",
    version="1.0.0"
)

# ─── Middleware ───────────────────────────────────────────────────────────────

# Session middleware (required for OAuth state parameter)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=3600,  # 1 hour for OAuth state
)

# CORS configuration — explicit origins required for credentials/cookies
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "https://foxenterprises.co.in",
    "https://www.foxenterprises.co.in",
    "http://localhost:8000",
]
# Remove empty strings and duplicates
allowed_origins = list(set(o for o in allowed_origins if o))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Set-Cookie"],
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
app.include_router(performance.router, prefix="/api")
app.include_router(websocket.router, prefix="")

@app.get("/")
def root():
    return {
        "message": "FOXFLOW ERP API is running",
        "docs": "/docs",
        "health": "/api/health"
    }


@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "FOXFLOW ERP API is healthy"}


# ─── Background Tasks ────────────────────────────────────────────────────────

from app.tasks.cleanup import cleanup_old_attendance_photos
from app.session_store import session_store
from app.cache import user_cache


async def periodic_session_cleanup():
    """Clean up expired sessions and cache entries every hour."""
    while True:
        await asyncio.sleep(3600)  # 1 hour
        expired_sessions = session_store.cleanup_expired()
        expired_cache = user_cache.cleanup_expired()
        if expired_sessions or expired_cache:
            print(f"[Cleanup] Removed {expired_sessions} expired sessions, {expired_cache} stale cache entries")


@app.on_event("startup")
async def startup_event():
    # Initialize database tables with connection retries
    init_db()
    # Start the background task to delete old attendance photos (older than 60 days)
    asyncio.create_task(cleanup_old_attendance_photos())
    # Start periodic session/cache cleanup
    asyncio.create_task(periodic_session_cleanup())
