from sqlalchemy import String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Lecturer(Base):
    __tablename__ = "lecturers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lecturer")
    department: Mapped["Department"] = relationship("Department", back_populates="lecturers")
    teaching_assignments: Mapped[list["TeachingAssignment"]] = relationship(
        "TeachingAssignment", back_populates="lecturer"
    )
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
        "AttendanceSession", back_populates="lecturer"
    )
