import enum
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.attendance_record import AttendanceStatus


class CorrectionRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AttendanceCorrectionRequest(Base):
    __tablename__ = "attendance_correction_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    attendance_record_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_records.id"), nullable=False
    )
    requested_status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CorrectionRequestStatus] = mapped_column(
        SAEnum(CorrectionRequestStatus),
        default=CorrectionRequestStatus.PENDING,
        nullable=False,
    )
    reviewer_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
