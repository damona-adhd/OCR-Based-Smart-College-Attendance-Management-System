from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.models.attendance_session import AttendanceSession, SessionStatus, SourceType
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.source_file import SourceFile
from app.schemas.ocr import OCRProcessingResult, OCRConfirmRequest
from app.schemas.attendance import AttendanceRecordOut
from app.services.ocr.ocr_service import process_register_image
from app.services.attendance.attendance_service import save_draft_records, finalize_session
from app.schemas.attendance import AttendanceRecordIn
from app.services.audit_service import log_event

router = APIRouter(prefix="/ocr", tags=["OCR"])


async def _get_lecturer(db: AsyncSession, user: User):
    result = await db.execute(select(Lecturer).where(Lecturer.user_id == user.id))
    return result.scalar_one_or_none()


@router.post("/process/{session_id}", response_model=OCRProcessingResult)
async def run_ocr_on_session(
    session_id: int,
    provider: Optional[str] = Query(None, description="Force provider: auto, gemini, pymupdf, tesseract"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger document extraction on the uploaded image or PDF for a session.
    Supports Gemini Vision, PyMuPDF Direct Table Extraction, OpenCV Grid Detection, and Tesseract Fallback.
    Returns a structured draft for teacher review.
    """
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    if not session.source_file_id:
        raise HTTPException(
            status_code=400, detail="No document uploaded for this session. Upload a register PDF or image first."
        )

    try:
        result = await process_register_image(
            db,
            source_file_id=session.source_file_id,
            session_id=session_id,
            class_id=session.class_id,
            forced_provider=provider,
        )
        await log_event(
            db, "document_extracted", current_user.id, "attendance_session", session_id,
            details={
                "source_file_id": session.source_file_id,
                "provider": result.extraction_provider,
                "total_candidate_rows": result.total_candidate_rows,
                "matched_students": result.matched_students,
            },
        )
        await db.commit()
        return result
    except RuntimeError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Extraction engine unavailable: {str(e)}. Please use manual attendance entry instead.",
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Document extraction failed: {str(e)}",
        )


@router.post("/confirm/{session_id}", response_model=dict)
async def confirm_ocr_attendance(
    session_id: int,
    body: OCRConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lecturer confirms the reviewed extraction results.
    Strictly prevents finalizing with 0 records or invalid/unassigned students.
    """
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in (SessionStatus.FINALIZED, "finalized", "FINALIZED"):
        raise HTTPException(status_code=400, detail="Attendance session is already finalized")

    if current_user.role == UserRole.LECTURER:
        lecturer = await _get_lecturer(db, current_user)
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    # STRICT SAFEGUARD: Reject empty corrections
    if not body.corrections:
        raise HTTPException(
            status_code=400,
            detail="Cannot confirm or finalize an attendance session with zero valid records. Review rows and assign students, or use manual entry.",
        )

    # Validate all rows have a valid student and status
    records_in = []
    seen_students = {}  # student_id -> row_index
    for row in body.corrections:
        if not row.student_id or row.student_id <= 0:
            raise HTTPException(
                status_code=400,
                detail=f"Row {row.row_index} has no student selected. Assign all rows to valid enrolled students before confirming.",
            )

        # Verify student exists in DB
        student_obj = await db.get(Student, row.student_id)
        if not student_obj:
            raise HTTPException(
                status_code=400,
                detail=f"Student ID {row.student_id} not found in database.",
            )

        if row.student_id in seen_students:
            first_row = seen_students[row.student_id]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Duplicate student detected: {student_obj.full_name} ({student_obj.usn}) "
                    f"is assigned to both Row {first_row} and Row {row.row_index}. "
                    f"Each student can only be marked once per session. Please reassign or remove the duplicate row."
                ),
            )
        seen_students[row.student_id] = row.row_index

        if row.attendance_status not in ("present", "absent"):
            raise HTTPException(
                status_code=400,
                detail=f"Row {row.row_index} has invalid attendance status '{row.attendance_status}'. Must be 'present' or 'absent'.",
            )
        records_in.append(
            AttendanceRecordIn(
                student_id=row.student_id,
                status=AttendanceStatus(row.attendance_status),
            )
        )

    if not records_in:
        raise HTTPException(status_code=400, detail="No valid records provided for finalization.")

    # Save as draft (OCR source type)
    await save_draft_records(db, session_id, records_in, source_type=SourceType.OCR)

    # Update session source type
    session.source_type = SourceType.OCR
    await db.flush()

    # Finalize
    await finalize_session(db, session_id, actor_user_id=current_user.id)

    await log_event(
        db, "ocr_attendance_confirmed", current_user.id, "attendance_session", session_id,
        details={"record_count": len(records_in)},
    )
    await db.commit()

    return {
        "message": "Attendance confirmed and finalized successfully",
        "session_id": session_id,
        "record_count": len(records_in),
    }
