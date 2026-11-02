from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import timezone, datetime

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.lecturer import Lecturer
from app.schemas.lecturer import LecturerCreate, LecturerUpdate, LecturerOut, LecturerWithUser
from app.services.audit_service import log_event

router = APIRouter(prefix="/lecturers", tags=["Lecturers"])


@router.get("", response_model=List[LecturerWithUser])
async def list_lecturers(
    department_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    q = select(Lecturer)
    if department_id:
        q = q.where(Lecturer.department_id == department_id)
    result = await db.execute(q.offset(skip).limit(limit))
    lecturers = result.scalars().all()

    out = []
    for lec in lecturers:
        d = LecturerWithUser.model_validate(lec)
        user = await db.get(User, lec.user_id)
        if user:
            d.username = user.username
            d.email = user.email
        out.append(d)
    return out


@router.post("", response_model=LecturerOut, status_code=201)
async def create_lecturer(
    body: LecturerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(select(Lecturer).where(Lecturer.employee_id == body.employee_id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Employee ID already exists")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
        role=UserRole.LECTURER,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.flush()

    lecturer = Lecturer(
        user_id=user.id,
        employee_id=body.employee_id,
        full_name=body.full_name,
        department_id=body.department_id,
    )
    db.add(lecturer)
    await db.flush()
    await log_event(db, "lecturer_created", current_user.id, "lecturer", lecturer.id,
                    details={"employee_id": body.employee_id})
    await db.commit()
    await db.refresh(lecturer)
    return lecturer


@router.get("/{lecturer_id}", response_model=LecturerWithUser)
async def get_lecturer(
    lecturer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lecturer = await db.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer not found")
    if current_user.role == UserRole.LECTURER:
        # Lecturers can only see their own profile
        if lecturer.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    d = LecturerWithUser.model_validate(lecturer)
    user = await db.get(User, lecturer.user_id)
    if user:
        d.username = user.username
        d.email = user.email
    return d


@router.patch("/{lecturer_id}", response_model=LecturerOut)
async def update_lecturer(
    lecturer_id: int,
    body: LecturerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    lecturer = await db.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(lecturer, k, v)
    await db.flush()
    await log_event(db, "lecturer_updated", current_user.id, "lecturer", lecturer_id)
    await db.commit()
    await db.refresh(lecturer)
    return lecturer


@router.delete("/{lecturer_id}", status_code=204)
async def deactivate_lecturer(
    lecturer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    lecturer = await db.get(Lecturer, lecturer_id)
    if not lecturer:
        raise HTTPException(status_code=404, detail="Lecturer not found")
    lecturer.is_active = False
    await db.flush()
    await log_event(db, "lecturer_deactivated", current_user.id, "lecturer", lecturer_id)
    await db.commit()
