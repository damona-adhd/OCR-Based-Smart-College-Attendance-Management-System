"""
Attendance calculation and report generation.
"""
import csv
import io
from typing import List, Optional, Tuple
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.models.student import Student
from app.models.subject import Subject
from app.models.class_ import Class
from app.models.app_setting import AppSetting
from app.schemas.reports import (
    SubjectAttendanceSummary,
    StudentAttendanceReport,
    ClassAttendanceRow,
    ClassAttendanceReport,
    DailyAttendanceRow,
)


async def get_min_attendance(db: AsyncSession) -> float:
    result = await db.execute(
        select(AppSetting).where(AppSetting.key == "min_attendance_percentage")
    )
    setting = result.scalar_one_or_none()
    if setting:
        try:
            return float(setting.value)
        except ValueError:
            pass
    return 75.0


async def get_student_report(
    db: AsyncSession,
    student_id: int,
) -> StudentAttendanceReport:
    """Compute attendance per subject for a given student."""
    student = await db.get(Student, student_id)
    if not student:
        raise ValueError("Student not found")

    min_pct = await get_min_attendance(db)

    # Get all finalized sessions for the student's class
    sessions_result = await db.execute(
        select(AttendanceSession).where(
            and_(
                AttendanceSession.class_id == student.class_id,
                AttendanceSession.status == SessionStatus.FINALIZED,
            )
        )
    )
    sessions = sessions_result.scalars().all()

    # Group by subject
    subject_sessions: dict = {}
    for s in sessions:
        subject_sessions.setdefault(s.subject_id, []).append(s)

    summaries = []
    total_attended = 0
    total_sessions_all = 0

    for subject_id, sess_list in subject_sessions.items():
        subject = await db.get(Subject, subject_id)
        if not subject:
            continue

        total = len(sess_list)
        attended = 0
        for sess in sess_list:
            rec_result = await db.execute(
                select(AttendanceRecord).where(
                    and_(
                        AttendanceRecord.attendance_session_id == sess.id,
                        AttendanceRecord.student_id == student_id,
                        AttendanceRecord.status == AttendanceStatus.PRESENT,
                    )
                )
            )
            if rec_result.scalar_one_or_none():
                attended += 1

        pct = (attended / total * 100) if total > 0 else 0.0
        total_attended += attended
        total_sessions_all += total

        summaries.append(
            SubjectAttendanceSummary(
                subject_id=subject_id,
                subject_code=subject.subject_code,
                subject_name=subject.subject_name,
                total_sessions=total,
                attended_sessions=attended,
                attendance_percentage=round(pct, 2),
                is_shortage=pct < min_pct,
            )
        )

    overall = (
        round(total_attended / total_sessions_all * 100, 2)
        if total_sessions_all > 0
        else 0.0
    )

    return StudentAttendanceReport(
        student_id=student_id,
        usn=student.usn,
        full_name=student.full_name,
        subjects=summaries,
        overall_percentage=overall,
    )


async def get_class_report(
    db: AsyncSession,
    class_id: int,
    subject_id: int,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> ClassAttendanceReport:
    """Compute per-student attendance for a class and subject."""
    min_pct = await get_min_attendance(db)

    filters = [
        AttendanceSession.class_id == class_id,
        AttendanceSession.subject_id == subject_id,
        AttendanceSession.status == SessionStatus.FINALIZED,
    ]
    if date_from:
        filters.append(AttendanceSession.attendance_date >= date_from)
    if date_to:
        filters.append(AttendanceSession.attendance_date <= date_to)

    sessions_result = await db.execute(
        select(AttendanceSession).where(and_(*filters))
    )
    sessions = sessions_result.scalars().all()
    session_ids = [s.id for s in sessions]
    total_sessions = len(session_ids)

    # Get all active students in class
    students_result = await db.execute(
        select(Student).where(
            and_(Student.class_id == class_id, Student.is_active == True)
        )
    )
    students = students_result.scalars().all()

    rows = []
    for student in students:
        if session_ids:
            attended_result = await db.execute(
                select(func.count(AttendanceRecord.id)).where(
                    and_(
                        AttendanceRecord.attendance_session_id.in_(session_ids),
                        AttendanceRecord.student_id == student.id,
                        AttendanceRecord.status == AttendanceStatus.PRESENT,
                    )
                )
            )
            attended = attended_result.scalar() or 0
        else:
            attended = 0

        pct = (attended / total_sessions * 100) if total_sessions > 0 else 0.0
        rows.append(
            ClassAttendanceRow(
                student_id=student.id,
                usn=student.usn,
                full_name=student.full_name,
                attended=attended,
                total=total_sessions,
                percentage=round(pct, 2),
                is_shortage=pct < min_pct,
            )
        )

    cls = await db.get(Class, class_id)
    subject = await db.get(Subject, subject_id)

    return ClassAttendanceReport(
        class_id=class_id,
        class_name=cls.name if cls else str(class_id),
        subject_id=subject_id,
        subject_name=subject.subject_name if subject else str(subject_id),
        date_from=date_from,
        date_to=date_to,
        rows=rows,
    )


async def get_daily_report(
    db: AsyncSession,
    class_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> List[DailyAttendanceRow]:
    filters = [AttendanceSession.status == SessionStatus.FINALIZED]
    if class_id:
        filters.append(AttendanceSession.class_id == class_id)
    if date_from:
        filters.append(AttendanceSession.attendance_date >= date_from)
    if date_to:
        filters.append(AttendanceSession.attendance_date <= date_to)

    sessions_result = await db.execute(
        select(AttendanceSession).where(and_(*filters)).order_by(
            AttendanceSession.attendance_date.desc()
        )
    )
    sessions = sessions_result.scalars().all()

    rows = []
    for sess in sessions:
        recs_result = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.attendance_session_id == sess.id
            )
        )
        recs = recs_result.scalars().all()
        present = sum(1 for r in recs if r.status == AttendanceStatus.PRESENT)
        absent = len(recs) - present
        total = len(recs)
        pct = (present / total * 100) if total > 0 else 0.0

        subject = await db.get(Subject, sess.subject_id)
        cls = await db.get(Class, sess.class_id)

        rows.append(
            DailyAttendanceRow(
                attendance_date=sess.attendance_date,
                subject_code=subject.subject_code if subject else "",
                subject_name=subject.subject_name if subject else "",
                class_name=cls.name if cls else "",
                present_count=present,
                absent_count=absent,
                total_count=total,
                attendance_percentage=round(pct, 2),
            )
        )
    return rows


def generate_class_csv(report: ClassAttendanceReport) -> str:
    """Generate CSV string from a class attendance report."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "USN", "Student Name", "Classes Attended",
        "Total Classes", "Attendance %", "Shortage"
    ])
    for row in report.rows:
        writer.writerow([
            row.usn,
            row.full_name,
            row.attended,
            row.total,
            f"{row.percentage:.1f}%",
            "Yes" if row.is_shortage else "No",
        ])

    return output.getvalue()
