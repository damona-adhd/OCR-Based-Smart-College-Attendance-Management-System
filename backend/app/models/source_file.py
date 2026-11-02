import enum
from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional
from app.core.database import Base


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # attendance_session_id is set AFTER the session is created (nullable)
    attendance_session_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("attendance_sessions.id", use_alter=True, name="fk_source_files_session"),
        nullable=True,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    uploader_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # roster | register
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(ProcessingStatus), default=ProcessingStatus.PENDING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    # No back-reference relationship to AttendanceSession here —
    # the session already owns a relationship to SourceFile via source_file_id.
    # A two-way FK between these tables causes ambiguous join errors.
