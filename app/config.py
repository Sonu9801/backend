from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./foxflow.db"
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived access token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30    # Long-lived refresh token
    SESSION_EXPIRE_DAYS: int = 30          # Server-side session TTL
    UPLOAD_DIR: str = "uploads"
    REDIS_URL: str = "redis://redis:6379/0"  # Redis for persistent sessions

    # Cookie settings
    COOKIE_DOMAIN: str = ""        # Empty = current domain
    COOKIE_SECURE: bool = False    # Set True in production (requires HTTPS)
    COOKIE_SAMESITE: str = "lax"   # "lax" for cross-origin OAuth redirects

    # CORS / Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    GEMINI_API_KEY: str = ""


    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
