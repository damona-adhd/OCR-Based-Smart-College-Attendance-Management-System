from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    APP_NAME: str = "Smart College Attendance Management System"

    # Database
    # For local dev without PostgreSQL, use SQLite:
    #   DATABASE_URL=sqlite+aiosqlite:///./attendance.db
    DATABASE_URL: str = "postgresql+asyncpg://attendance_user:change_me@localhost:5432/attendance_db"
    SYNC_DATABASE_URL: Optional[str] = None  # For Alembic (sync driver)

    # JWT
    SECRET_KEY: str = "change_me_to_a_very_long_random_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10

    # Document extraction & OCR configuration
    TESSERACT_CMD: str = "tesseract"
    OCR_MIN_CONFIDENCE: int = 50
    ATTENDANCE_EXTRACTION_PROVIDER: str = "auto"  # auto | gemini | pymupdf | tesseract
    EXTRACTION_PROVIDER: str = "auto"  # backward-compat alias
    ENABLE_OPENCV_GRID_DETECTION: bool = True
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"  # e.g. gemini-2.5-flash, gemini-2.0-flash

    @property
    def resolved_tesseract_cmd(self) -> str:
        """Auto-detect Tesseract executable on Windows if not explicitly set."""
        if self.TESSERACT_CMD and os.path.isabs(self.TESSERACT_CMD) and os.path.exists(self.TESSERACT_CMD):
            return self.TESSERACT_CMD
        win_std = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.name == "nt" and os.path.exists(win_std):
            return win_std
        win_x86 = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
        if os.name == "nt" and os.path.exists(win_x86):
            return win_x86
        return self.TESSERACT_CMD or "tesseract"

    # Attendance
    MIN_ATTENDANCE_PERCENTAGE: float = 75.0

    # Bootstrap admin (used only by setup script)
    BOOTSTRAP_ADMIN_USERNAME: str = "admin"
    BOOTSTRAP_ADMIN_EMAIL: str = "admin@college.edu"
    BOOTSTRAP_ADMIN_PASSWORD: str = "change_me_admin_password"

    @property
    def allowed_origins_list(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def sync_db_url(self) -> str:
        """Return synchronous DB URL for Alembic."""
        if self.SYNC_DATABASE_URL:
            return self.SYNC_DATABASE_URL
        # SQLite async → sync driver swap
        if "aiosqlite" in self.DATABASE_URL:
            return self.DATABASE_URL.replace("+aiosqlite", "")
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = {
        "env_file": [".env", "../.env"],   # works from both backend/ and project root
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
