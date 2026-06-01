import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "FECHAT Backend"
    DEBUG: bool = True
    
    # JWT Settings
    JWT_SECRET: str = "dev-secret-change-me-in-production-1234567890"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 1 day
    
    # Database Settings
    # Use SQLite for development, can be configured to PostgreSQL for AWS RDS
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    
    # CORS Settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]
    
    # File Upload Directory
    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Ensure Upload Directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
