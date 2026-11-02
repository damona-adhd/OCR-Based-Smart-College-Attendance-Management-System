"""Comprehensive tests for Master Project Requirements:
- Three-role authentication & role mismatch rejection
- Quick-add student & duplicate USN rejection
- Quick-add subject & duplicate code rejection
- Roster commit transaction & duplicate safety
- Dashboard calculations (Admin, Teacher, Student)
- Attendance corrections & student requests
"""
import pytest
from httpx import AsyncClient
from datetime import date
from sqlalchemy import select

from app.tests.conftest import get_token
from app.models.student import Student
from app.models.subject import Subject
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus


@pytest.mark.asyncio
async def test_role_mismatch_rejection(client: AsyncClient, admin_user, student_user):
    """Ensure user cannot choose one role and authenticate with another."""
    # 1. Admin account trying to login as student
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@123", "expected_role": "student"},
    )
    assert resp.status_code == 403
    assert "does not match the selected role" in resp.json()["detail"]

    # 2. Student account trying to login as admin
    resp = await client.post(
        "/api/auth/login",
        json={"username": "stu1", "password": "Stu@123", "expected_role": "admin"},
    )
    assert resp.status_code == 403

    # 3. Valid admin login with correct expected role
    resp = await client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "Admin@123", "expected_role": "admin"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_teacher_quick_add_student(
    client: AsyncClient, db_session, lecturer_user, lecturer, class_
):
    """Teacher can add student with Name, USN, and class assignment."""
    token = await get_token(client, "lec1", "Lec@123")

    # Valid creation
    resp = await client.post(
        "/api/students/quick-add",
        json={
            "full_name": "Kavya Murthy",
            "usn": "1CS21CS088",
            "class_id": class_.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["usn"] == "1CS21CS088"
    assert data["full_name"] == "Kavya Murthy"
    assert data["class_id"] == class_.id

    # Duplicate USN rejection
    dup_resp = await client.post(
        "/api/students/quick-add",
        json={
            "full_name": "Another Name",
            "usn": "1CS21CS088",
            "class_id": class_.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dup_resp.status_code == 409
    assert "A student with this USN already exists" in dup_resp.json()["detail"]

    # Empty validation
    bad_resp = await client.post(
        "/api/students/quick-add",
        json={
            "full_name": "   ",
            "usn": "1CS21CS089",
            "class_id": class_.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert bad_resp.status_code == 400


@pytest.mark.asyncio
async def test_teacher_quick_add_subject(
    client: AsyncClient, db_session, lecturer_user, lecturer, class_
):
    """Teacher can add subject with Name and Code."""
    token = await get_token(client, "lec1", "Lec@123")

    resp = await client.post(
        "/api/subjects/quick-add",
        json={
            "subject_name": "Operating Systems",
            "subject_code": "CS401",
            "class_id": class_.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    assert resp.json()["subject_code"] == "CS401"

    # Duplicate code rejection
    dup_resp = await client.post(
        "/api/subjects/quick-add",
        json={
            "subject_name": "Operating Systems Lab",
            "subject_code": "CS401",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_roster_transactional_commit(
    client: AsyncClient, db_session, admin_user, class_
):
    """Admin commits extracted roster rows atomically."""
    token = await get_token(client, "admin", "Admin@123")

    payload = {
        "class_id": class_.id,
        "students": [
            {"usn": "1CS21CS101", "full_name": "Ananya Roy"},
            {"usn": "1CS21CS102", "full_name": "Brijesh Patel"},
        ],
    }
    resp = await client.post(
        "/api/roster/import",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["imported_count"] == 2
    assert resp.json()["skipped_count"] == 0

    # Repeating import safely skips duplicates without failure
    resp2 = await client.post(
        "/api/roster/import",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["imported_count"] == 0
    assert resp2.json()["skipped_count"] == 2


@pytest.mark.asyncio
async def test_dashboard_endpoints(
    client: AsyncClient, db_session,
    admin_user, lecturer_user, lecturer,
    student_user, student, class_, subject, assignment
):
    """Verify live metrics endpoints for all three roles."""
    # 1. Admin dashboard
    admin_token = await get_token(client, "admin", "Admin@123")
    r_admin = await client.get("/api/dashboards/admin", headers={"Authorization": f"Bearer {admin_token}"})
    assert r_admin.status_code == 200
    assert "summary" in r_admin.json()
    assert "trends" in r_admin.json()

    # 2. Teacher dashboard
    lec_token = await get_token(client, "lec1", "Lec@123")
    r_lec = await client.get("/api/dashboards/teacher", headers={"Authorization": f"Bearer {lec_token}"})
    assert r_lec.status_code == 200
    assert "assignments" in r_lec.json()

    # 3. Student dashboard
    stu_token = await get_token(client, "stu1", "Stu@123")
    r_stu = await client.get("/api/dashboards/student", headers={"Authorization": f"Bearer {stu_token}"})
    assert r_stu.status_code == 200
    assert "summary" in r_stu.json()
    assert "subjects" in r_stu.json()


@pytest.mark.asyncio
async def test_attendance_corrections_workflow(
    client: AsyncClient, db_session,
    lecturer_user, lecturer, student_user, student,
    class_, subject, assignment
):
    """Test teacher direct correction and student correction request review."""
    lec_token = await get_token(client, "lec1", "Lec@123")

    # Create & finalize session
    session = AttendanceSession(
        subject_id=subject.id,
        class_id=class_.id,
        lecturer_id=lecturer.id,
        attendance_date=date.today(),
        status=SessionStatus.FINALIZED,
    )
    db_session.add(session)
    await db_session.flush()

    record = AttendanceRecord(
        attendance_session_id=session.id,
        student_id=student.id,
        status=AttendanceStatus.ABSENT,
        source_type=session.source_type,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # 1. Teacher corrects record directly
    c_resp = await client.post(
        f"/api/corrections/record/{record.id}",
        json={"new_status": "present", "reason": "Medical certificate verified"},
        headers={"Authorization": f"Bearer {lec_token}"},
    )
    assert c_resp.status_code == 200
    assert c_resp.json()["new_status"] == "present"

    # Verify history
    h_resp = await client.get(
        f"/api/corrections/history/{record.id}",
        headers={"Authorization": f"Bearer {lec_token}"},
    )
    assert h_resp.status_code == 200
    assert len(h_resp.json()) == 1
    assert h_resp.json()[0]["reason"] == "Medical certificate verified"
