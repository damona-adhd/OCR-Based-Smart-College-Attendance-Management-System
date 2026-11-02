from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import date
import io

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.teaching_assignment import TeachingAssignment
from app.schemas.reports import StudentAttendanceReport, ClassAttendanceReport, AuditEventOut
from app.services.reports.report_service import (
    get_student_report,
    get_class_report,
    get_daily_report,
    generate_class_csv,
)
from app.models.audit_event import AuditEvent

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/student/{student_id}", response_model=StudentAttendanceReport)
async def student_attendance_report(
    student_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Students see their own report; admin/lecturer can see any."""
    if current_user.role == UserRole.STUDENT:
        result = await db.execute(
            select(Student).where(Student.user_id == current_user.id)
        )
        student = result.scalar_one_or_none()
        if not student or student.id != student_id:
            raise HTTPException(status_code=403, detail="Access denied")

    try:
        return await get_student_report(db, student_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/my", response_model=StudentAttendanceReport)
async def my_attendance_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Student's own report shortcut."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student access only")
    result = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return await get_student_report(db, student.id)


@router.get("/class", response_model=ClassAttendanceReport)
async def class_attendance_report(
    class_id: int,
    subject_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.LECTURER:
        # Verify assignment
        lec_result = await db.execute(
            select(Lecturer).where(Lecturer.user_id == current_user.id)
        )
        lecturer = lec_result.scalar_one_or_none()
        if not lecturer:
            raise HTTPException(status_code=403, detail="No lecturer profile")
        asn = await db.execute(
            select(TeachingAssignment).where(
                TeachingAssignment.lecturer_id == lecturer.id,
                TeachingAssignment.class_id == class_id,
                TeachingAssignment.subject_id == subject_id,
            )
        )
        if not asn.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not assigned to this class/subject")
    elif current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")

    return await get_class_report(db, class_id, subject_id, date_from, date_to)


@router.get("/class/csv")
async def class_attendance_csv(
    class_id: int,
    subject_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")

    report = await get_class_report(db, class_id, subject_id, date_from, date_to)
    csv_content = generate_class_csv(report)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=attendance_{class_id}_{subject_id}.csv"
        },
    )


@router.get("/daily")
async def daily_attendance_report(
    class_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Access denied")
    return await get_daily_report(db, class_id, date_from, date_to)


@router.get("/audit", response_model=list)
async def audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    action: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    q = select(AuditEvent).order_by(AuditEvent.created_at.desc()).offset(skip).limit(limit)
    if action:
        q = q.where(AuditEvent.action == action)
    result = await db.execute(q)
    events = result.scalars().all()

    out = []
    for ev in events:
        actor_username = None
        if ev.actor_user_id:
            u = await db.get(User, ev.actor_user_id)
            if u:
                actor_username = u.username
        out.append({
            "id": ev.id,
            "actor_user_id": ev.actor_user_id,
            "actor_username": actor_username,
            "action": ev.action,
            "entity_type": ev.entity_type,
            "entity_id": ev.entity_id,
            "details": ev.details,
            "created_at": ev.created_at.isoformat(),
        })
    return out
