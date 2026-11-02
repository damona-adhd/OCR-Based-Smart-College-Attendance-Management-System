from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    subject_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="subjects")
    teaching_assignments: Mapped[list["TeachingAssignment"]] = relationship(
        "TeachingAssignment", back_populates="subject"
    )
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
        "AttendanceSession", back_populates="subject"
    )
