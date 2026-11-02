from sqlalchemy import String, Integer, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional
from app.core.database import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True, unique=True
    )
    usn: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    course: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="student")
    department: Mapped["Department"] = relationship("Department", back_populates="students")
    class_: Mapped["Class"] = relationship("Class", back_populates="students")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="student"
    )
