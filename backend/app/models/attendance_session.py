import enum
from datetime import datetime, date, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Date, Enum as SAEnum, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.core.database import Base


class SessionStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    CANCELLED = "cancelled"


class SourceType(str, enum.Enum):
    MANUAL = "manual"
    OCR = "ocr"


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"
    __table_args__ = (
        UniqueConstraint(
            "subject_id", "class_id", "attendance_date", "period",
            name="uq_session_subject_class_date_period"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("lecturers.id"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    period: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus), default=SessionStatus.DRAFT, nullable=False
    )
    source_type: Mapped[SourceType] = mapped_column(
        SAEnum(SourceType), default=SourceType.MANUAL, nullable=False
    )
    # FK to source_files — use_alter breaks the circular dependency
    source_file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("source_files.id", use_alter=True, name="fk_sessions_source_file"),
        nullable=True,
    )
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    subject: Mapped["Subject"] = relationship("Subject", back_populates="attendance_sessions")
    class_: Mapped["Class"] = relationship("Class", back_populates="attendance_sessions")
    lecturer: Mapped["Lecturer"] = relationship("Lecturer", back_populates="attendance_sessions")

    # Explicit foreign_keys required because source_files also has a FK back to us
    source_file: Mapped[Optional["SourceFile"]] = relationship(
        "SourceFile",
        foreign_keys=[source_file_id],
        # No back_populates — SourceFile has no relationship attribute
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )
