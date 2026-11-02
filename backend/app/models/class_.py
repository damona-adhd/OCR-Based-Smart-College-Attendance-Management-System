from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "2024-25"
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    section: Mapped[str] = mapped_column(String(20), nullable=False, default="A", server_default="A")
    course: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)

    # Relationships
    department: Mapped["Department"] = relationship("Department", back_populates="classes")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="class_")
    teaching_assignments: Mapped[list["TeachingAssignment"]] = relationship(
        "TeachingAssignment", back_populates="class_"
    )
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
        "AttendanceSession", back_populates="class_"
    )
