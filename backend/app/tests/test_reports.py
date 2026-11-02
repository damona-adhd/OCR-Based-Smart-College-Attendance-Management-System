import pytest
from httpx import AsyncClient
from datetime import date
from app.tests.conftest import get_token
from app.models.attendance_session import AttendanceSession, SessionStatus, SourceType
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.services.reports.report_service import get_student_report
from datetime import datetime, timezone


async def _create_finalized_session(
    db_session, lecturer, subject, class_, student, att_date, status
):
    """Helper: create and finalize a session with one attendance record."""
    session = AttendanceSession(
        subject_id=subject.id,
        class_id=class_.id,
        lecturer_id=lecturer.id,
        attendance_date=att_date,
        status=SessionStatus.FINALIZED,
        source_type=SourceType.MANUAL,
        finalized_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.flush()

    rec = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=student.id,
        status=status,
        source_type=SourceType.MANUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(rec)
    await db_session.flush()
    return session


@pytest.mark.asyncio
async def test_attendance_percentage_calculation(
    db_session, student, subject, class_, lecturer, min_attendance_setting
):
    """4 sessions, 3 present = 75% exactly."""
    await _create_finalized_session(db_session, lecturer, subject, class_, student, date(2025, 1, 1), AttendanceStatus.PRESENT)
    await _create_finalized_session(db_session, lecturer, subject, class_, student, date(2025, 1, 2), AttendanceStatus.PRESENT)
    await _create_finalized_session(db_session, lecturer, subject, class_, student, date(2025, 1, 3), AttendanceStatus.PRESENT)
    await _create_finalized_session(db_session, lecturer, subject, class_, student, date(2025, 1, 4), AttendanceStatus.ABSENT)

    report = await get_student_report(db_session, student.id)
    assert len(report.subjects) == 1
    sub = report.subjects[0]
    assert sub.attended_sessions == 3
    assert sub.total_sessions == 4
    assert sub.attendance_percentage == 75.0
    assert not sub.is_shortage  # 75% == threshold, not shortage


@pytest.mark.asyncio
async def test_zero_sessions_no_division_error(
    db_session, student, min_attendance_setting
):
    report = await get_student_report(db_session, student.id)
    assert report.overall_percentage == 0.0
    assert report.subjects == []


@pytest.mark.asyncio
async def test_student_cannot_see_others_report(
    client: AsyncClient, db_session,
    student_user, student,
    subject, class_, lecturer, assignment
):
    token = await get_token(client, "stu1", "Stu@123")
    # Try to access a different student id (student.id + 999)
    resp = await client.get(
        f"/api/reports/student/{student.id + 999}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_draft_session_not_in_report(
    db_session, student, subject, class_, lecturer, min_attendance_setting
):
    """Draft sessions must not affect attendance calculations."""
    # Create a finalized session
    await _create_finalized_session(db_session, lecturer, subject, class_, student, date(2025, 2, 1), AttendanceStatus.PRESENT)

    # Add a draft session (should not be counted)
    draft = AttendanceSession(
        subject_id=subject.id,
        class_id=class_.id,
        lecturer_id=lecturer.id,
        attendance_date=date(2025, 2, 2),
        status=SessionStatus.DRAFT,
        source_type=SourceType.MANUAL,
    )
    db_session.add(draft)
    await db_session.flush()
    rec = AttendanceRecord(
        attendance_session_id=draft.id,
        student_id=student.id,
        status=AttendanceStatus.ABSENT,
        source_type=SourceType.MANUAL,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(rec)
    await db_session.flush()

    report = await get_student_report(db_session, student.id)
    sub = report.subjects[0]
    assert sub.total_sessions == 1  # only finalized
    assert sub.attended_sessions == 1
    assert sub.attendance_percentage == 100.0
