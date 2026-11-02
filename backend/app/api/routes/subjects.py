from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_admin, require_lecturer, get_current_user
from app.models.subject import Subject
from app.models.user import User, UserRole
from app.models.lecturer import Lecturer
from app.models.department import Department
from app.models.class_ import Class
from app.models.teaching_assignment import TeachingAssignment
from app.schemas.subject import SubjectCreate, SubjectQuickCreate, SubjectUpdate, SubjectOut
from app.services.audit_service import log_event
from app.services.settings_service import get_bool_setting

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", response_model=List[SubjectOut])
async def list_subjects(
    department_id: Optional[int] = None,
    semester: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Subject)
    if department_id:
        q = q.where(Subject.department_id == department_id)
    if semester:
        q = q.where(Subject.semester == semester)
    result = await db.execute(q.order_by(Subject.subject_name))
    return result.scalars().all()


@router.post("", response_model=SubjectOut, status_code=201)
async def create_subject(
    body: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    clean_code = body.subject_code.strip().upper()
    existing = await db.execute(
        select(Subject).where(Subject.subject_code == clean_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Subject code already exists")
    data = body.model_dump()
    data["subject_code"] = clean_code
    data["subject_name"] = body.subject_name.strip()
    subject = Subject(**data)
    db.add(subject)
    await db.flush()
    await log_event(db, "subject_created", current_user.id, "subject", subject.id)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.post("/quick-add", response_model=SubjectOut, status_code=201)
async def quick_add_subject(
    body: SubjectQuickCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """
    Teacher or Admin can quickly add a subject with Name and Code.
    Automatically defaults department and semester if not provided.
    """
    if current_user.role == UserRole.LECTURER:
        allowed = await get_bool_setting(db, "allow_teacher_create_subject", default=True)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Adding subjects is restricted to administrators by college policy",
            )

    clean_name = body.subject_name.strip()
    clean_code = body.subject_code.strip().upper()

    if not clean_name:
        raise HTTPException(status_code=400, detail="Subject name cannot be empty")
    if not clean_code:
        raise HTTPException(status_code=400, detail="Subject code cannot be empty")

    existing = await db.execute(select(Subject).where(Subject.subject_code == clean_code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Subject code already exists")

    # Resolve department
    dept_id = body.department_id
    sem = body.semester or 1
    target_class = None

    if body.class_id:
        target_class = await db.get(Class, body.class_id)
        if target_class:
            dept_id = dept_id or target_class.department_id
            sem = body.semester or target_class.semester

    if not dept_id and current_user.role == UserRole.LECTURER:
        res_lec = await db.execute(select(Lecturer).where(Lecturer.user_id == current_user.id))
        lec = res_lec.scalar_one_or_none()
        if lec:
            dept_id = lec.department_id

    if not dept_id:
        # Fallback to first department in system
        first_dept = await db.execute(select(Department).limit(1))
        f_dept = first_dept.scalar_one_or_none()
        if f_dept:
            dept_id = f_dept.id
        else:
            raise HTTPException(status_code=400, detail="Please create a department first before adding subjects")

    subject = Subject(
        subject_name=clean_name,
        subject_code=clean_code,
        department_id=dept_id,
        semester=sem,
    )
    db.add(subject)
    await db.flush()

    # If class_id was provided and teacher created it, also create teaching assignment if not already exists
    if target_class and current_user.role == UserRole.LECTURER:
        res_lec = await db.execute(select(Lecturer).where(Lecturer.user_id == current_user.id))
        lec = res_lec.scalar_one_or_none()
        if lec:
            existing_asn = await db.execute(
                select(TeachingAssignment).where(
                    TeachingAssignment.lecturer_id == lec.id,
                    TeachingAssignment.class_id == target_class.id,
                    TeachingAssignment.subject_id == subject.id,
                )
            )
            if not existing_asn.scalar_one_or_none():
                asn = TeachingAssignment(
                    lecturer_id=lec.id,
                    class_id=target_class.id,
                    subject_id=subject.id,
                )
                db.add(asn)
                await db.flush()

    await log_event(
        db,
        action="subject_quick_added",
        actor_user_id=current_user.id,
        entity_type="subject",
        entity_id=subject.id,
        details={"subject_code": clean_code, "subject_name": clean_name},
    )
    await db.commit()
    await db.refresh(subject)
    return subject


@router.get("/{subject_id}", response_model=SubjectOut)
async def get_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subject).where(Subject.id == subject_id)
    )
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject


@router.patch("/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: int,
    body: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(subject, k, v)
    await db.flush()
    await log_event(db, "subject_updated", current_user.id, "subject", subject_id)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=204)
async def delete_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await db.delete(subject)
    await log_event(db, "subject_deleted", current_user.id, "subject", subject_id)
    await db.commit()
