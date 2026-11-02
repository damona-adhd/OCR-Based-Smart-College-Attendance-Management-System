"""
Test configuration and fixtures.
Uses an in-memory SQLite database for speed.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

from app.main import app
from app.core.limiter import limiter
from app.core.database import Base, get_db

limiter.enabled = False
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.department import Department
from app.models.class_ import Class
from app.models.subject import Subject
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.teaching_assignment import TeachingAssignment
from app.models.app_setting import AppSetting

from datetime import datetime, timezone

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    Session = async_sessionmaker(db_engine, expire_on_commit=False)
    async with Session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ---- Data fixtures ----

@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        username="admin",
        email="admin@test.edu",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def dept(db_session: AsyncSession) -> Department:
    d = Department(name="Computer Science", code="CSE")
    db_session.add(d)
    await db_session.flush()
    return d


@pytest_asyncio.fixture
async def class_(db_session: AsyncSession, dept: Department) -> Class:
    c = Class(name="CSE 3A", academic_year="2024-25", semester=3, department_id=dept.id)
    db_session.add(c)
    await db_session.flush()
    return c


@pytest_asyncio.fixture
async def subject(db_session: AsyncSession, dept: Department) -> Subject:
    s = Subject(subject_code="CS301", subject_name="Data Structures", semester=3, department_id=dept.id)
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def lecturer_user(db_session: AsyncSession) -> User:
    user = User(
        username="lec1",
        email="lec1@test.edu",
        password_hash=hash_password("Lec@123"),
        role=UserRole.LECTURER,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def lecturer(db_session: AsyncSession, lecturer_user: User, dept: Department) -> Lecturer:
    lec = Lecturer(
        user_id=lecturer_user.id,
        employee_id="EMP001",
        full_name="Dr. Test Lecturer",
        department_id=dept.id,
    )
    db_session.add(lec)
    await db_session.flush()
    return lec


@pytest_asyncio.fixture
async def student_user(db_session: AsyncSession) -> User:
    user = User(
        username="stu1",
        email="stu1@test.edu",
        password_hash=hash_password("Stu@123"),
        role=UserRole.STUDENT,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def student(db_session: AsyncSession, student_user: User, dept: Department, class_: Class) -> Student:
    s = Student(
        user_id=student_user.id,
        usn="1CS21CS001",
        full_name="Test Student",
        department_id=dept.id,
        academic_year="2024-25",
        semester=3,
        class_id=class_.id,
    )
    db_session.add(s)
    await db_session.flush()
    return s


@pytest_asyncio.fixture
async def assignment(
    db_session: AsyncSession, lecturer: Lecturer, subject: Subject, class_: Class
) -> TeachingAssignment:
    a = TeachingAssignment(
        lecturer_id=lecturer.id,
        subject_id=subject.id,
        class_id=class_.id,
    )
    db_session.add(a)
    await db_session.flush()
    return a


@pytest_asyncio.fixture
async def min_attendance_setting(db_session: AsyncSession) -> AppSetting:
    s = AppSetting(key="min_attendance_percentage", value="75")
    db_session.add(s)
    await db_session.flush()
    return s


async def get_token(client: AsyncClient, username: str, password: str) -> str:
    resp = await client.post(
        "/api/auth/login",
        data={"username": username, "password": password},
    )
    return resp.json()["access_token"]
