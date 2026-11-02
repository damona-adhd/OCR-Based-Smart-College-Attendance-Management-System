from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus, SourceType
from app.models.attendance_record import AttendanceRecord
from app.models.lecturer import Lecturer
from app.models.student import Student
from app.schemas.attendance import (
    SessionCreate, SessionOut, SessionDetailOut, AttendanceRecordOut,
    ManualAttendanceSubmit, FinalizeSession, CancelSession,
    AttendanceCorrectionRequest,
)
from app.services.attendance.attendance_service import (
    verify_lecturer_assignment,
    create_session,
    save_draft_records,
    finalize_session,
    cancel_session,
    correct_finalized_record,
)
from app.services.audit_service import log_event

router = APIRouter(prefix="/attendance", tags=["Attendance"])


async def _get_lecturer(db: AsyncSession, user: User) -> Optional[Lecturer]:
    result = await db.execute(select(Lecturer).where(Lecturer.user_id == user.id))
    return result.scalar_one_or_none()


@router.get("/sessions", response_model=List[SessionOut])
async def list_sessions(
    class_id: Optional[int] = None,
    subject_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(AttendanceSession)
    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer:
            return []
        q = q.where(AttendanceSession.lecturer_id == lecturer.id)
    if class_id:
        q = q.where(AttendanceSession.class_id == class_id)
    if subject_id:
        q = q.where(AttendanceSession.subject_id == subject_id)
    if status:
        q = q.where(AttendanceSession.status == status)
    if date_from:
        q = q.where(AttendanceSession.attendance_date >= date_from)
    if date_to:
        q = q.where(AttendanceSession.attendance_date <= date_to)

    result = await db.execute(
        q.order_by(AttendanceSession.attendance_date.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/sessions", response_model=SessionOut, status_code=201)
async def create_attendance_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    lecturer = await _get_lecturer(db, current_user)
    if not lecturer:
        raise HTTPException(status_code=403, detail="No lecturer profile found")

    await verify_lecturer_assignment(db, lecturer.id, body.subject_id, body.class_id)

    session = await create_session(
        db,
        lecturer_id=lecturer.id,
        subject_id=body.subject_id,
        class_id=body.class_id,
        attendance_date=body.attendance_date,
        source_type=body.source_type,
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=SessionDetailOut)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.attendance_records))
        .where(AttendanceSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Lecturer can only see own sessions
    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    out = SessionDetailOut.model_validate(session)
    # Enrich records with student info
    enriched = []
    for rec in session.attendance_records:
        student = await db.get(Student, rec.student_id)
        row = AttendanceRecordOut.model_validate(rec)
        if student:
            row.student_usn = student.usn
            row.student_name = student.full_name
        enriched.append(row)
    out.records = enriched

    # Enrich session with names
    from app.models.subject import Subject
    from app.models.class_ import Class
    subj = await db.get(Subject, session.subject_id)
    cls = await db.get(Class, session.class_id)
    lec = await db.get(Lecturer, session.lecturer_id)
    out.subject_name = subj.subject_name if subj else None
    out.class_name = cls.name if cls else None
    out.lecturer_name = lec.full_name if lec else None
    return out


@router.post("/sessions/{session_id}/records", response_model=List[AttendanceRecordOut])
async def submit_manual_attendance(
    session_id: int,
    body: ManualAttendanceSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save (or replace) draft attendance records."""
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    records = await save_draft_records(
        db, session_id, body.records, source_type=SourceType.MANUAL
    )
    await db.commit()

    out = []
    for rec in records:
        await db.refresh(rec)
        student = await db.get(Student, rec.student_id)
        row = AttendanceRecordOut.model_validate(rec)
        if student:
            row.student_usn = student.usn
            row.student_name = student.full_name
        out.append(row)
    return out


@router.post("/sessions/{session_id}/finalize", response_model=SessionOut)
async def finalize_attendance_session(
    session_id: int,
    body: FinalizeSession,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    session = await finalize_session(db, session_id, actor_user_id=current_user.id)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/sessions/{session_id}/cancel", response_model=SessionOut)
async def cancel_attendance_session(
    session_id: int,
    body: CancelSession,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    session = await cancel_session(db, session_id, body.reason, actor_user_id=current_user.id)
    await db.commit()
    await db.refresh(session)
    return session


@router.post("/sessions/{session_id}/correct", response_model=AttendanceRecordOut)
async def correct_attendance(
    session_id: int,
    body: AttendanceCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Authorized correction of a finalized attendance record."""
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    record = await correct_finalized_record(
        db,
        session_id=session_id,
        student_id=body.student_id,
        new_status=body.new_status,
        reason=body.reason,
        actor_user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(record)
    student = await db.get(Student, record.student_id)
    out = AttendanceRecordOut.model_validate(record)
    if student:
        out.student_usn = student.usn
        out.student_name = student.full_name
    return out


# ---- Student-facing attendance view ----

@router.get("/my", response_model=List[AttendanceRecordOut])
async def get_my_attendance(
    subject_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Students view their own attendance."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student access only")

    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    q = (
        select(AttendanceRecord)
        .join(AttendanceSession)
        .where(
            and_(
                AttendanceRecord.student_id == student.id,
                AttendanceSession.status == SessionStatus.FINALIZED,
            )
        )
    )
    if subject_id:
        q = q.where(AttendanceSession.subject_id == subject_id)

    recs_result = await db.execute(q)
    records = recs_result.scalars().all()

    out = []
    for rec in records:
        row = AttendanceRecordOut.model_validate(rec)
        row.student_usn = student.usn
        row.student_name = student.full_name
        out.append(row)
    return out
