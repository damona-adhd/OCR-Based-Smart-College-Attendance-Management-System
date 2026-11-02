import pytest
from datetime import date
from httpx import AsyncClient
from app.tests.conftest import get_token
from app.models.attendance_session import AttendanceSession, SessionStatus, SourceType
from app.models.attendance_record import AttendanceRecord, AttendanceStatus


@pytest.mark.asyncio
async def test_create_session(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_, assignment
):
    token = await get_token(client, "lec1", "Lec@123")
    resp = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": str(date.today()),
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_duplicate_session_rejected(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_, assignment
):
    token = await get_token(client, "lec1", "Lec@123")
    payload = {
        "subject_id": subject.id,
        "class_id": class_.id,
        "attendance_date": "2025-01-15",
        "source_type": "manual",
    }
    r1 = await client.post(
        "/api/attendance/sessions", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/attendance/sessions", json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_manual_attendance_and_finalize(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_, assignment, student
):
    token = await get_token(client, "lec1", "Lec@123")

    # Create session
    r = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": "2025-01-16",
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = r.json()["id"]

    # Submit records
    r2 = await client.post(
        f"/api/attendance/sessions/{session_id}/records",
        json={"records": [{"student_id": student.id, "status": "present"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200

    # Finalize
    r3 = await client.post(
        f"/api/attendance/sessions/{session_id}/finalize",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 200
    assert r3.json()["status"] == "finalized"


@pytest.mark.asyncio
async def test_finalize_empty_session_rejected(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_, assignment
):
    token = await get_token(client, "lec1", "Lec@123")

    r = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": "2025-01-17",
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = r.json()["id"]

    r2 = await client.post(
        f"/api/attendance/sessions/{session_id}/finalize",
        json={"confirm": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_student_cannot_create_session(
    client: AsyncClient, db_session,
    student_user, student, subject, class_
):
    token = await get_token(client, "stu1", "Stu@123")
    resp = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": "2025-01-18",
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_unassigned_lecturer_cannot_create_session(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_
    # NOTE: no assignment fixture here
):
    token = await get_token(client, "lec1", "Lec@123")
    resp = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": "2025-01-19",
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_record_in_submission_rejected(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, subject, class_, assignment, student
):
    token = await get_token(client, "lec1", "Lec@123")

    r = await client.post(
        "/api/attendance/sessions",
        json={
            "subject_id": subject.id,
            "class_id": class_.id,
            "attendance_date": "2025-01-20",
            "source_type": "manual",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    session_id = r.json()["id"]

    r2 = await client.post(
        f"/api/attendance/sessions/{session_id}/records",
        json={
            "records": [
                {"student_id": student.id, "status": "present"},
                {"student_id": student.id, "status": "absent"},  # duplicate
            ]
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400
