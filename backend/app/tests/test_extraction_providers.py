"""
Integration and unit tests for document extraction providers,
roster matching, and finalization safeguards.
"""
import pytest
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.class_ import Class
from app.models.subject import Subject
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.source_file import SourceFile, ProcessingStatus
from app.services.extraction.orchestrator import extraction_orchestrator
from app.services.extraction.pymupdf_provider import PyMuPDFExtractionProvider
from app.services.extraction.gemini_provider import GeminiExtractionProvider


@pytest.mark.asyncio
async def test_pymupdf_direct_extraction_on_ledger_pdf():
    """Verify PyMuPDF extracts 62 student rows from the digital ledger PDF."""
    pdf_path = r"D:\attendance_project2\backend\uploads\cc20629220c54cadaedf1f24a4819fa4.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Test ledger PDF not found on disk")

    provider = PyMuPDFExtractionProvider()
    result = await provider.extract(pdf_path, "application/pdf")

    assert result.status == "success"
    assert result.total_candidate_rows >= 60
    assert result.present_count > 0
    assert result.absent_count > 0

    # Verify first row
    first_row = result.rows[0]
    assert first_row.usn == "01JST24UCS007"
    assert "Aishadipto" in (first_row.student_name or "")
    assert first_row.attendance_status.value == "present"


@pytest.mark.asyncio
async def test_extraction_preserves_rows_on_empty_class(db_session: AsyncSession):
    """Verify orchestrator preserves all candidate rows even when class has 0 students."""
    pdf_path = r"D:\attendance_project2\backend\uploads\cc20629220c54cadaedf1f24a4819fa4.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip("Test ledger PDF not found on disk")

    # Create an empty class
    empty_class = Class(name="Empty Test Class", semester=4, academic_year="2025-26", department_id=1)
    db_session.add(empty_class)
    await db_session.flush()

    res = await extraction_orchestrator.process_document(
        db=db_session,
        file_path=pdf_path,
        mime_type="application/pdf",
        session_id=999,
        source_file_id=999,
        class_id=empty_class.id,
    )

    # Must NOT report 0 rows found!
    assert res.total_candidate_rows >= 60
    assert res.valid_rows >= 60
    assert res.unmatched_students >= 60
    assert "No students are currently enrolled in this class" in (res.processing_note or "")


@pytest.mark.asyncio
async def test_cannot_finalize_empty_ocr_attendance(
    client: AsyncClient, lecturer_user: User, lecturer: Lecturer, db_session: AsyncSession
):
    """Verify backend strictly rejects finalization with zero records."""
    from app.tests.conftest import get_token
    token = await get_token(client, "lec1", "Lec@123")
    headers = {"Authorization": f"Bearer {token}"}

    from datetime import date
    session = AttendanceSession(
        subject_id=1,
        class_id=1,
        lecturer_id=lecturer.id,
        attendance_date=date(2026, 3, 20),
        status=SessionStatus.DRAFT,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Attempt to confirm with empty list
    resp = await client.post(
        f"/api/ocr/confirm/{session.id}",
        json={"session_id": session.id, "corrections": []},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "zero valid records" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_gemini_unconfigured_error_handling():
    """Verify Gemini provider reports unconfigured gracefully without crashing."""
    from app.core.config import settings
    orig_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = None

    try:
        provider = GeminiExtractionProvider()
        result = await provider.extract("dummy.pdf", "application/pdf")
        assert result.status == "unconfigured"
        assert any("GEMINI_API_KEY is not configured" in err for err in result.errors)
    finally:
        settings.GEMINI_API_KEY = orig_key


@pytest.mark.asyncio
async def test_confirm_ocr_attendance_success(
    client: AsyncClient, lecturer_user: User, lecturer: Lecturer, student: Student, db_session: AsyncSession
):
    """Verify confirming valid OCR records finalizes session and records attendance."""
    from app.tests.conftest import get_token
    from datetime import date

    token = await get_token(client, "lec1", "Lec@123")
    headers = {"Authorization": f"Bearer {token}"}

    session = AttendanceSession(
        subject_id=1,
        class_id=1,
        lecturer_id=lecturer.id,
        attendance_date=date(2026, 3, 22),
        status=SessionStatus.DRAFT,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    resp = await client.post(
        f"/api/ocr/confirm/{session.id}",
        json={
            "session_id": session.id,
            "corrections": [
                {"row_index": 1, "student_id": student.id, "attendance_status": "present"}
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["record_count"] == 1
    assert "successfully" in data["message"].lower()

    # Verify session is now finalized in database
    await db_session.refresh(session)
    assert session.status == SessionStatus.FINALIZED

