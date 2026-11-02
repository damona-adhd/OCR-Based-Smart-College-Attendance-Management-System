from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import timezone, datetime

from app.core.database import get_db
from app.core.dependencies import require_admin, require_lecturer, get_current_user
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.class_ import Class
from app.schemas.student import StudentCreate, StudentQuickCreate, StudentUpdate, StudentOut, StudentWithUser
from app.services.audit_service import log_event
from app.services.settings_service import get_bool_setting

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("/roster/{class_id}", response_model=List[StudentOut])
async def get_class_roster(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get active students in a class.
    Lecturers can call this for any class (the attendance routes
    already enforce assignment checks). Admins always allowed.
    Students are denied.
    """
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    q = select(Student).where(
        and_(Student.class_id == class_id, Student.is_active == True)
    ).order_by(Student.usn)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("", response_model=List[StudentWithUser])
async def list_students(
    class_id: Optional[int] = None,
    department_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    q = select(Student)
    if class_id:
        q = q.where(Student.class_id == class_id)
    if department_id:
        q = q.where(Student.department_id == department_id)
    if is_active is not None:
        q = q.where(Student.is_active == is_active)
    result = await db.execute(q.offset(skip).limit(limit))
    students = result.scalars().all()

    out = []
    for s in students:
        d = StudentWithUser.model_validate(s)
        if s.user_id:
            user = await db.get(User, s.user_id)
            if user:
                d.username = user.username
                d.email = user.email
        out.append(d)
    return out


@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    body: StudentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Check USN uniqueness
    existing = await db.execute(select(Student).where(Student.usn == body.usn))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="USN already exists")

    user_id = None
    if body.username and body.email and body.password:
        # Create login account
        user = User(
            username=body.username,
            email=body.email,
            password_hash=hash_password(body.password),
            role=UserRole.STUDENT,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(user)
        await db.flush()
        user_id = user.id

    student = Student(
        user_id=user_id,
        usn=body.usn,
        full_name=body.full_name,
        department_id=body.department_id,
        academic_year=body.academic_year,
        semester=body.semester,
        class_id=body.class_id,
    )
    db.add(student)
    await db.flush()
    await log_event(db, "student_created", current_user.id, "student", student.id,
                    details={"usn": body.usn})
    await db.commit()
    await db.refresh(student)
    return student


@router.post("/quick-add", response_model=StudentOut, status_code=201)
async def quick_add_student(
    body: StudentQuickCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """
    Teacher or Admin can quickly add a student with just Name and USN.
    Class assignment automatically binds the department, academic year, and semester.
    """
    if current_user.role == UserRole.LECTURER:
        allowed = await get_bool_setting(db, "allow_teacher_create_student", default=True)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Adding students is restricted to administrators by college policy",
            )

    clean_name = body.full_name.strip()
    clean_usn = body.usn.strip().upper()

    if not clean_name:
        raise HTTPException(status_code=400, detail="Student name cannot be empty")
    if not clean_usn:
        raise HTTPException(status_code=400, detail="USN cannot be empty")

    # Check for duplicate USN
    existing = await db.execute(select(Student).where(Student.usn == clean_usn))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A student with this USN already exists.")

    target_class = await db.get(Class, body.class_id)
    if not target_class:
        raise HTTPException(status_code=404, detail="Selected class not found")

    student = Student(
        usn=clean_usn,
        full_name=clean_name,
        department_id=target_class.department_id,
        academic_year=target_class.academic_year,
        semester=target_class.semester,
        course=target_class.course,
        class_id=target_class.id,
        is_active=True,
    )
    db.add(student)
    await db.flush()
    await log_event(
        db,
        action="student_quick_added",
        actor_user_id=current_user.id,
        entity_type="student",
        entity_id=student.id,
        details={"usn": clean_usn, "class_id": target_class.id},
    )
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentWithUser)
async def get_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Students can only see their own record
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    if current_user.role == UserRole.STUDENT:
        if not student.user_id or student.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    d = StudentWithUser.model_validate(student)
    if student.user_id:
        user = await db.get(User, student.user_id)
        if user:
            d.username = user.username
            d.email = user.email
    return d


@router.patch("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: int,
    body: StudentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(student, k, v)
    await db.flush()
    await log_event(db, "student_updated", current_user.id, "student", student_id)
    await db.commit()
    await db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
async def deactivate_student(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    await db.flush()
    await log_event(db, "student_deactivated", current_user.id, "student", student_id)
    await db.commit()
