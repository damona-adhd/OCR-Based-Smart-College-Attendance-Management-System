import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Float, Boolean, ForeignKey, DateTime, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.attendance_session import SourceType


class AttendanceStatus(str, enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint(
            "attendance_session_id", "student_id",
            name="uq_record_session_student"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    attendance_session_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_sessions.id"), nullable=False
    )
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(SAEnum(SourceType), nullable=False)
    extraction_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession", back_populates="attendance_records"
    )
    student: Mapped["Student"] = relationship("Student", back_populates="attendance_records")
