import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger("uvicorn.error")

def _normalize_database_url(url: str) -> str:
    """Auto-resolve dialect mismatch between psycopg (v3) and psycopg2 (v2)."""
    if url.startswith("sqlite"):
        return url
    if url.startswith("postgresql+psycopg://"):
        try:
            import psycopg  # noqa: F401
            return url
        except ImportError:
            logger.warning("[DB] 'psycopg' (v3) not installed. Falling back to 'psycopg2'.")
            return url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql://"):
        try:
            import psycopg2  # noqa: F401
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
        except ImportError:
            return url
    return url

db_url = _normalize_database_url(settings.DATABASE_URL)

if db_url.startswith("sqlite"):
    engine = create_engine(
        db_url, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=5,
        pool_recycle=300,
        connect_args={
            "connect_timeout": 5,
            "keepalives": 1,
            "keepalives_idle": 10,
            "keepalives_interval": 5,
            "keepalives_count": 3
        }
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()

def init_db(retries: int = 5, delay: int = 1):
    """Initializes tables in database with connection retry logic."""
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"[DB] Attempting connection to database (attempt {attempt}/{retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("[DB] Database tables initialized successfully.")
            return
        except Exception as e:
            if attempt == retries:
                logger.error(f"[DB] Failed to connect to database after {retries} attempts: {e}")
                raise e
            logger.warning(f"[DB] Connection failed ({e}). Retrying in {delay}s...")
            time.sleep(delay)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
