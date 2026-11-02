from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.attendance_record import AttendanceStatus


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_record_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_records.id"), nullable=False, index=True
    )
    previous_status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus), nullable=False
    )
    new_status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus), nullable=False
    )
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
