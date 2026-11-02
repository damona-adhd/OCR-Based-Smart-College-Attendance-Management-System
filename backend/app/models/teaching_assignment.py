from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignments"
    __table_args__ = (
        UniqueConstraint("lecturer_id", "subject_id", "class_id", name="uq_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    lecturer_id: Mapped[int] = mapped_column(ForeignKey("lecturers.id"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id"), nullable=False)

    # Relationships
    lecturer: Mapped["Lecturer"] = relationship("Lecturer", back_populates="teaching_assignments")
    subject: Mapped["Subject"] = relationship("Subject", back_populates="teaching_assignments")
    class_: Mapped["Class"] = relationship("Class", back_populates="teaching_assignments")
