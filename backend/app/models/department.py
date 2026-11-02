from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)

    # Relationships
    classes: Mapped[list["Class"]] = relationship("Class", back_populates="department")
    subjects: Mapped[list["Subject"]] = relationship("Subject", back_populates="department")
    students: Mapped[list["Student"]] = relationship("Student", back_populates="department")
    lecturers: Mapped[list["Lecturer"]] = relationship("Lecturer", back_populates="department")
