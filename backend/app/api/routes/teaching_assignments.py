from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.models.teaching_assignment import TeachingAssignment
from app.models.lecturer import Lecturer
from app.models.user import User, UserRole
from app.schemas.teaching_assignment import AssignmentCreate, AssignmentOut
from app.services.audit_service import log_event

router = APIRouter(prefix="/assignments", tags=["Teaching Assignments"])

# Helper — eager-load all nested relations in one query
_LOAD_OPTS = [
    selectinload(TeachingAssignment.lecturer),
    selectinload(TeachingAssignment.subject),
    selectinload(TeachingAssignment.class_),
]


@router.get("", response_model=List[AssignmentOut])
async def list_assignments(
    lecturer_id: Optional[int] = None,
    class_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(TeachingAssignment).options(*_LOAD_OPTS)

    # Lecturers can only see their own assignments
    if current_user.role == UserRole.LECTURER:
        lec_result = await db.execute(
            select(Lecturer).where(Lecturer.user_id == current_user.id)
        )
        lecturer = lec_result.scalar_one_or_none()
        if not lecturer:
            return []
        q = q.where(TeachingAssignment.lecturer_id == lecturer.id)
    else:
        if lecturer_id:
            q = q.where(TeachingAssignment.lecturer_id == lecturer_id)

    if class_id:
        q = q.where(TeachingAssignment.class_id == class_id)

    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    body: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(
        select(TeachingAssignment).where(
            and_(
                TeachingAssignment.lecturer_id == body.lecturer_id,
                TeachingAssignment.subject_id == body.subject_id,
                TeachingAssignment.class_id == body.class_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Assignment already exists")

    assignment = TeachingAssignment(
        lecturer_id=body.lecturer_id,
        subject_id=body.subject_id,
        class_id=body.class_id,
    )
    db.add(assignment)
    await db.flush()
    await log_event(db, "assignment_created", current_user.id, "teaching_assignment", assignment.id)
    await db.commit()

    result = await db.execute(
        select(TeachingAssignment).options(
            selectinload(TeachingAssignment.lecturer),
            selectinload(TeachingAssignment.subject),
            selectinload(TeachingAssignment.class_),
        ).where(TeachingAssignment.id == assignment.id)
    )
    return result.scalar_one()


@router.delete("/{assignment_id}", status_code=204)
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    assignment = await db.get(TeachingAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await log_event(db, "assignment_deleted", current_user.id, "teaching_assignment", assignment_id)
    await db.commit()
