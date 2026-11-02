"""
DEV-ONLY seed script — creates sample data for local testing.
DO NOT run in production.
Usage: python scripts/seed_dev.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.class_ import Class
from app.models.subject import Subject
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.teaching_assignment import TeachingAssignment
from app.models.app_setting import AppSetting
import app.models  # noqa


async def seed():
    if settings.APP_ENV == "production":
        print("ERROR: seed_dev.py cannot be run in production.")
        return

    _is_sqlite = "sqlite" in settings.DATABASE_URL
    _kwargs = {"echo": False}
    if _is_sqlite:
        _kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(settings.DATABASE_URL, **_kwargs)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        # Check if already seeded
        existing = await db.execute(select(Department))
        if existing.scalars().first():
            print("Seed data already exists. Skipping.")
            return

        print("Seeding development data...")

        # Departments
        cse = Department(name="Computer Science & Engineering", code="CSE")
        ece = Department(name="Electronics & Communication", code="ECE")
        db.add_all([cse, ece])
        await db.flush()

        # Classes
        cse3a = Class(name="CSE 3A", academic_year="2024-25", semester=3, department_id=cse.id)
        cse3b = Class(name="CSE 3B", academic_year="2024-25", semester=3, department_id=cse.id)
        db.add_all([cse3a, cse3b])
        await db.flush()

        # Subjects
        ds   = Subject(subject_code="CS301", subject_name="Data Structures", semester=3, department_id=cse.id)
        algo = Subject(subject_code="CS302", subject_name="Design & Analysis of Algorithms", semester=3, department_id=cse.id)
        dbms = Subject(subject_code="CS303", subject_name="Database Management Systems", semester=3, department_id=cse.id)
        db.add_all([ds, algo, dbms])
        await db.flush()

        # Lecturer 1
        lec1_user = User(
            username="dr.sharma", email="sharma@college.edu",
            password_hash=hash_password("Lecturer@123"),
            role=UserRole.LECTURER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(lec1_user)
        await db.flush()
        lec1 = Lecturer(user_id=lec1_user.id, employee_id="EMP001",
                        full_name="Dr. Rajesh Sharma", department_id=cse.id)
        db.add(lec1)
        await db.flush()

        # Lecturer 2
        lec2_user = User(
            username="prof.patel", email="patel@college.edu",
            password_hash=hash_password("Lecturer@123"),
            role=UserRole.LECTURER,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(lec2_user)
        await db.flush()
        lec2 = Lecturer(user_id=lec2_user.id, employee_id="EMP002",
                        full_name="Prof. Meena Patel", department_id=cse.id)
        db.add(lec2)
        await db.flush()

        # Teaching assignments
        db.add_all([
            TeachingAssignment(lecturer_id=lec1.id, subject_id=ds.id,   class_id=cse3a.id),
            TeachingAssignment(lecturer_id=lec1.id, subject_id=algo.id, class_id=cse3a.id),
            TeachingAssignment(lecturer_id=lec2.id, subject_id=dbms.id, class_id=cse3a.id),
            TeachingAssignment(lecturer_id=lec1.id, subject_id=ds.id,   class_id=cse3b.id),
        ])
        await db.flush()

        # Students with login accounts
        student_data = [
            ("1CS21CS001", "Aditya Kumar"),
            ("1CS21CS002", "Bhavana Singh"),
            ("1CS21CS003", "Chetan Reddy"),
            ("1CS21CS004", "Divya Nair"),
            ("1CS21CS005", "Eshan Gupta"),
            ("1CS21CS006", "Fatima Khan"),
            ("1CS21CS007", "Gaurav Verma"),
            ("1CS21CS008", "Harini Rao"),
            ("1CS21CS009", "Ishaan Desai"),
            ("1CS21CS010", "Jyoti Mishra"),
        ]
        for i, (usn, name) in enumerate(student_data):
            user_id = None
            if i < 3:
                stu_user = User(
                    username=usn.lower(),
                    email=f"{usn.lower()}@student.college.edu",
                    password_hash=hash_password("Student@123"),
                    role=UserRole.STUDENT,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(stu_user)
                await db.flush()
                user_id = stu_user.id

            db.add(Student(
                user_id=user_id, usn=usn, full_name=name,
                department_id=cse.id, academic_year="2024-25",
                semester=3, class_id=cse3a.id,
            ))
        await db.flush()

        # App settings
        db.add(AppSetting(
            key="min_attendance_percentage",
            value="75",
            description="Minimum attendance percentage required",
        ))

        await db.commit()

    await engine.dispose()

    print("\n[OK] Seed complete!")
    print("\n=== DEV ACCOUNTS (never use in production) ===")
    print("Lecturer 1 : dr.sharma     / Lecturer@123")
    print("Lecturer 2 : prof.patel    / Lecturer@123")
    print("Student 1  : 1cs21cs001    / Student@123")
    print("Student 2  : 1cs21cs002    / Student@123")
    print("Student 3  : 1cs21cs003    / Student@123")
    print("=== Run create_admin.py for the admin account ===")


if __name__ == "__main__":
    asyncio.run(seed())
