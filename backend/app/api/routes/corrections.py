"""Attendance corrections and student correction request review router."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_lecturer
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.attendance_correction import AttendanceCorrection
from app.models.correction_request import AttendanceCorrectionRequest, CorrectionRequestStatus
from app.services.audit_service import log_event
from app.services.settings_service import get_bool_setting

router = APIRouter(prefix="/corrections", tags=["Corrections"])


class DirectCorrectionInput(BaseModel):
    new_status: AttendanceStatus
    reason: str


class CorrectionRequestInput(BaseModel):
    attendance_record_id: int
    requested_status: AttendanceStatus
    reason: str


class ReviewRequestInput(BaseModel):
    status: CorrectionRequestStatus  # approved | rejected
    review_note: Optional[str] = None


@router.post("/record/{record_id}")
async def correct_record(
    record_id: int,
    body: DirectCorrectionInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """Teacher or Admin corrects a finalized attendance record with audit trail."""
    record = await db.get(AttendanceRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")

    session = await db.get(AttendanceSession, record.attendance_session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # If teacher, verify that this session was conducted by this teacher
    if current_user.role == UserRole.LECTURER:
        res_lec = await db.execute(select(Lecturer).where(Lecturer.user_id == current_user.id))
        lec = res_lec.scalar_one_or_none()
        if not lec or session.lecturer_id != lec.id:
            raise HTTPException(status_code=403, detail="You can only correct attendance for your own sessions")

    if not body.reason.strip():
        raise HTTPException(status_code=400, detail="A reason for correction is required")

    prev_status = record.status
    record.status = body.new_status
    record.is_corrected = True
    record.updated_at = datetime.now(timezone.utc)

    correction = AttendanceCorrection(
        attendance_record_id=record.id,
        previous_status=prev_status,
        new_status=body.new_status,
        actor_user_id=current_user.id,
        reason=body.reason.strip(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(correction)
    await db.flush()

    await log_event(
        db,
        action="attendance_corrected",
        actor_user_id=current_user.id,
        entity_type="attendance_record",
        entity_id=record.id,
        details={
            "session_id": session.id,
            "previous_status": prev_status.value,
            "new_status": body.new_status.value,
            "reason": body.reason.strip(),
        },
    )
    await db.commit()

    return {
        "success": True,
        "record_id": record.id,
        "previous_status": prev_status,
        "new_status": body.new_status,
        "reason": body.reason.strip(),
    }


@router.get("/history/{record_id}")
async def get_record_correction_history(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full audit history for changes made to a record."""
    res = await db.execute(
        select(AttendanceCorrection)
        .where(AttendanceCorrection.attendance_record_id == record_id)
        .order_by(AttendanceCorrection.created_at.desc())
    )
    corrections = res.scalars().all()
    out = []
    for c in corrections:
        actor = await db.get(User, c.actor_user_id)
        out.append({
            "id": c.id,
            "previous_status": c.previous_status,
            "new_status": c.new_status,
            "reason": c.reason,
            "actor_username": actor.username if actor else "Unknown",
            "created_at": c.created_at.isoformat(),
        })
    return out


@router.post("/request")
async def create_correction_request(
    body: CorrectionRequestInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Student submits an attendance correction request."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit correction requests")

    allowed = await get_bool_setting(db, "allow_student_correction_requests", default=True)
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail="Student correction requests are currently disabled by college administration.",
        )

    res_stu = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = res_stu.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    record = await db.get(AttendanceRecord, body.attendance_record_id)
    if not record or record.student_id != student.id:
        raise HTTPException(status_code=404, detail="Attendance record not found or not yours")

    # Check for pending duplicate request
    existing = await db.execute(
        select(AttendanceCorrectionRequest).where(
            AttendanceCorrectionRequest.attendance_record_id == record.id,
            AttendanceCorrectionRequest.status == CorrectionRequestStatus.PENDING,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A pending correction request already exists for this session")

    req = AttendanceCorrectionRequest(
        student_id=student.id,
        attendance_record_id=record.id,
        requested_status=body.requested_status,
        reason=body.reason.strip(),
        status=CorrectionRequestStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)

    return {"success": True, "request_id": req.id, "status": req.status}


@router.get("/requests")
async def list_correction_requests(
    status_filter: Optional[CorrectionRequestStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """Teacher or admin lists pending student correction requests."""
    q = select(AttendanceCorrectionRequest)
    if status_filter:
        q = q.where(AttendanceCorrectionRequest.status == status_filter)

    res = await db.execute(q.order_by(AttendanceCorrectionRequest.created_at.desc()))
    requests = res.scalars().all()
    out = []
    for r in requests:
        stu = await db.get(Student, r.student_id)
        rec = await db.get(AttendanceRecord, r.attendance_record_id)
        sess = await db.get(AttendanceSession, rec.attendance_session_id) if rec else None
        subj = await db.get(Subject, sess.subject_id) if sess else None

        out.append({
            "id": r.id,
            "student_id": r.student_id,
            "student_name": stu.full_name if stu else "Unknown",
            "student_usn": stu.usn if stu else "Unknown",
            "attendance_record_id": r.attendance_record_id,
            "current_status": rec.status.value if rec else "N/A",
            "requested_status": r.requested_status.value,
            "reason": r.reason,
            "status": r.status.value,
            "subject_name": subj.subject_name if subj else "N/A",
            "date": str(sess.attendance_date) if sess else "N/A",
            "created_at": r.created_at.isoformat(),
        })
    return out


@router.post("/requests/{request_id}/review")
async def review_correction_request(
    request_id: int,
    body: ReviewRequestInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """Teacher or admin approves or rejects a student correction request."""
    req = await db.get(AttendanceCorrectionRequest, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Correction request not found")

    if req.status != CorrectionRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="This request has already been reviewed")

    req.status = body.status
    req.reviewer_user_id = current_user.id
    req.review_note = body.review_note
    req.reviewed_at = datetime.now(timezone.utc)

    if body.status == CorrectionRequestStatus.APPROVED:
        record = await db.get(AttendanceRecord, req.attendance_record_id)
        if record:
            prev_status = record.status
            record.status = req.requested_status
            record.is_corrected = True

            correction = AttendanceCorrection(
                attendance_record_id=record.id,
                previous_status=prev_status,
                new_status=req.requested_status,
                actor_user_id=current_user.id,
                reason=f"Approved student request #{req.id}: {req.reason}",
                created_at=datetime.now(timezone.utc),
            )
            db.add(correction)

    await db.commit()
    return {"success": True, "request_id": req.id, "status": req.status}
