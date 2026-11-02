"""
Core attendance business logic.
"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException, status

from app.models.attendance_session import AttendanceSession, SessionStatus, SourceType
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.student import Student
from app.models.teaching_assignment import TeachingAssignment
from app.schemas.attendance import AttendanceRecordIn, ManualAttendanceSubmit
from app.services.audit_service import log_event


async def verify_lecturer_assignment(
    db: AsyncSession,
    lecturer_id: int,
    subject_id: int,
    class_id: int,
) -> None:
    """Raise 403 if the lecturer is not assigned to this subject+class."""
    result = await db.execute(
        select(TeachingAssignment).where(
            and_(
                TeachingAssignment.lecturer_id == lecturer_id,
                TeachingAssignment.subject_id == subject_id,
                TeachingAssignment.class_id == class_id,
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this class and subject",
        )


async def create_session(
    db: AsyncSession,
    lecturer_id: int,
    subject_id: int,
    class_id: int,
    attendance_date,
    source_type: SourceType = SourceType.MANUAL,
    actor_user_id: Optional[int] = None,
) -> AttendanceSession:
    """Create a draft session. Raises 409 if session already exists."""
    existing = await db.execute(
        select(AttendanceSession).where(
            and_(
                AttendanceSession.subject_id == subject_id,
                AttendanceSession.class_id == class_id,
                AttendanceSession.attendance_date == attendance_date,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An attendance session already exists for this class, subject, and date",
        )

    session = AttendanceSession(
        subject_id=subject_id,
        class_id=class_id,
        lecturer_id=lecturer_id,
        attendance_date=attendance_date,
        source_type=source_type,
        status=SessionStatus.DRAFT,
    )
    db.add(session)
    await db.flush()

    await log_event(
        db,
        action="session_created",
        actor_user_id=actor_user_id,
        entity_type="attendance_session",
        entity_id=session.id,
        details={"subject_id": subject_id, "class_id": class_id, "date": str(attendance_date)},
    )
    return session


async def save_draft_records(
    db: AsyncSession,
    session_id: int,
    records: List[AttendanceRecordIn],
    source_type: SourceType = SourceType.MANUAL,
) -> List[AttendanceRecord]:
    """
    Upsert attendance records for a draft session.
    Existing records are replaced; duplicates within the call are rejected.
    """
    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.FINALIZED:
        raise HTTPException(
            status_code=400, detail="Cannot modify a finalized session"
        )

    student_ids = [r.student_id for r in records]
    if len(student_ids) != len(set(student_ids)):
        raise HTTPException(
            status_code=400, detail="Duplicate student entries in submission"
        )

    # Delete existing records for this session (full replace)
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.attendance_session_id == session_id
        )
    )
    for rec in existing.scalars().all():
        await db.delete(rec)
    await db.flush()

    new_records = []
    for r in records:
        rec = AttendanceRecord(
            attendance_session_id=session_id,
            student_id=r.student_id,
            status=r.status,
            source_type=source_type,
        )
        db.add(rec)
        new_records.append(rec)

    await db.flush()
    return new_records


async def finalize_session(
    db: AsyncSession,
    session_id: int,
    actor_user_id: Optional[int] = None,
) -> AttendanceSession:
    """Mark session as finalized. Records become official."""
    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Session is already finalized")
    if session.status == SessionStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot finalize a cancelled session")

    # Ensure there are records
    result = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.attendance_session_id == session_id
        )
    )
    records = result.scalars().all()
    if not records:
        raise HTTPException(
            status_code=400,
            detail="Cannot finalize an empty attendance session",
        )

    session.status = SessionStatus.FINALIZED
    session.finalized_at = datetime.now(timezone.utc)
    await db.flush()

    await log_event(
        db,
        action="session_finalized",
        actor_user_id=actor_user_id,
        entity_type="attendance_session",
        entity_id=session_id,
        details={"record_count": len(records)},
    )
    return session


async def cancel_session(
    db: AsyncSession,
    session_id: int,
    reason: str,
    actor_user_id: Optional[int] = None,
) -> AttendanceSession:
    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.FINALIZED:
        raise HTTPException(
            status_code=400, detail="Cannot cancel a finalized session directly. Use correction workflow."
        )

    session.status = SessionStatus.CANCELLED
    await db.flush()

    await log_event(
        db,
        action="session_cancelled",
        actor_user_id=actor_user_id,
        entity_type="attendance_session",
        entity_id=session_id,
        details={"reason": reason},
    )
    return session


async def correct_finalized_record(
    db: AsyncSession,
    session_id: int,
    student_id: int,
    new_status: AttendanceStatus,
    reason: str,
    actor_user_id: Optional[int] = None,
) -> AttendanceRecord:
    """Authorized correction of a finalized session record — full audit trail."""
    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != SessionStatus.FINALIZED:
        raise HTTPException(status_code=400, detail="Session is not finalized")

    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.attendance_session_id == session_id,
                AttendanceRecord.student_id == student_id,
            )
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    old_status = record.status
    record.status = new_status
    await db.flush()

    await log_event(
        db,
        action="attendance_record_corrected",
        actor_user_id=actor_user_id,
        entity_type="attendance_record",
        entity_id=record.id,
        details={
            "session_id": session_id,
            "student_id": student_id,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "reason": reason,
        },
    )
    return record
