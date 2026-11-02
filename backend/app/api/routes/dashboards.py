"""Dashboard aggregation endpoints for Admin, Teacher, and Student roles."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_admin, require_lecturer, require_student
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.student import Student
from app.models.lecturer import Lecturer
from app.models.class_ import Class
from app.models.subject import Subject
from app.models.teaching_assignment import TeachingAssignment
from app.models.attendance_session import AttendanceSession, SessionStatus
from app.models.attendance_record import AttendanceRecord, AttendanceStatus
from app.services.settings_service import get_setting

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


# ---------------- Admin Dashboard ----------------
@router.get("/admin")
async def get_admin_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Aggregate live metrics and charts for the administrator dashboard."""
    # Active students count
    res_students = await db.execute(select(func.count(Student.id)).where(Student.is_active == True))
    total_students = res_students.scalar() or 0

    # Active lecturers count
    res_lecturers = await db.execute(select(func.count(Lecturer.id)).where(Lecturer.is_active == True))
    total_lecturers = res_lecturers.scalar() or 0

    # Active classes count
    res_classes = await db.execute(select(func.count(Class.id)))
    total_classes = res_classes.scalar() or 0

    # Total subjects count
    res_subjects = await db.execute(select(func.count(Subject.id)))
    total_subjects = res_subjects.scalar() or 0

    # Sessions stats
    res_sess_total = await db.execute(select(func.count(AttendanceSession.id)))
    total_sessions = res_sess_total.scalar() or 0

    res_sess_finalized = await db.execute(
        select(func.count(AttendanceSession.id)).where(AttendanceSession.status == SessionStatus.FINALIZED)
    )
    finalized_sessions = res_sess_finalized.scalar() or 0

    res_sess_draft = await db.execute(
        select(func.count(AttendanceSession.id)).where(AttendanceSession.status == SessionStatus.DRAFT)
    )
    draft_sessions = res_sess_draft.scalar() or 0

    # Records breakdown (from finalized sessions)
    res_records = await db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(AttendanceSession.status == SessionStatus.FINALIZED)
        .group_by(AttendanceRecord.status)
    )
    record_counts = {r[0]: r[1] for r in res_records.all()}
    total_present = record_counts.get(AttendanceStatus.PRESENT, 0)
    total_absent = record_counts.get(AttendanceStatus.ABSENT, 0)
    total_recorded = total_present + total_absent
    overall_percentage = round((total_present / total_recorded * 100), 1) if total_recorded > 0 else 0.0

    # Today's stats
    today_dt = date.today()
    res_today_sess = await db.execute(
        select(func.count(AttendanceSession.id)).where(AttendanceSession.attendance_date == today_dt)
    )
    sessions_today = res_today_sess.scalar() or 0

    res_today_records = await db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(AttendanceSession.attendance_date == today_dt, AttendanceSession.status == SessionStatus.FINALIZED)
        .group_by(AttendanceRecord.status)
    )
    today_counts = {r[0]: r[1] for r in res_today_records.all()}
    today_present = today_counts.get(AttendanceStatus.PRESENT, 0)
    today_absent = today_counts.get(AttendanceStatus.ABSENT, 0)
    today_total = today_present + today_absent
    today_pct = round((today_present / today_total * 100), 1) if today_total > 0 else 0.0

    # Recent sessions (latest 6)
    res_recent_sess = await db.execute(
        select(AttendanceSession)
        .order_by(AttendanceSession.attendance_date.desc(), AttendanceSession.id.desc())
        .limit(6)
    )
    recent_sess_rows = res_recent_sess.scalars().all()
    recent_activity = []
    for s in recent_sess_rows:
        subj = await db.get(Subject, s.subject_id)
        cls = await db.get(Class, s.class_id)
        lec = await db.get(Lecturer, s.lecturer_id)
        recent_activity.append({
            "id": s.id,
            "date": str(s.attendance_date),
            "period": s.period,
            "status": s.status.value,
            "subject_name": subj.subject_name if subj else "Unknown",
            "subject_code": subj.subject_code if subj else "",
            "class_name": cls.name if cls else "Unknown",
            "teacher_name": lec.full_name if lec else "Unknown",
        })

    # Attendance Trend (last 7 days with conducted sessions)
    res_daily_trend = await db.execute(
        select(
            AttendanceSession.attendance_date,
            func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_c"),
            func.sum(case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_c"),
        )
        .join(AttendanceRecord, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(AttendanceSession.status == SessionStatus.FINALIZED)
        .group_by(AttendanceSession.attendance_date)
        .order_by(AttendanceSession.attendance_date.desc())
        .limit(7)
    )
    trend_rows = res_daily_trend.all()
    attendance_trends = []
    for row in reversed(trend_rows):
        p = row.present_c or 0
        a = row.absent_c or 0
        tot = p + a
        pct = round((p / tot * 100), 1) if tot > 0 else 0.0
        attendance_trends.append({
            "date": str(row.attendance_date),
            "present": p,
            "absent": a,
            "percentage": pct,
        })

    # Class-wise comparison
    res_class_wise = await db.execute(
        select(
            Class.id,
            Class.name,
            func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_c"),
            func.sum(case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_c"),
        )
        .join(AttendanceSession, AttendanceSession.class_id == Class.id)
        .join(AttendanceRecord, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(AttendanceSession.status == SessionStatus.FINALIZED)
        .group_by(Class.id, Class.name)
        .limit(8)
    )
    class_wise = []
    for row in res_class_wise.all():
        p = row.present_c or 0
        a = row.absent_c or 0
        tot = p + a
        pct = round((p / tot * 100), 1) if tot > 0 else 0.0
        class_wise.append({
            "class_id": row.id,
            "class_name": row.name,
            "present": p,
            "absent": a,
            "percentage": pct,
        })

    # Subject-wise comparison
    res_subj_wise = await db.execute(
        select(
            Subject.id,
            Subject.subject_code,
            Subject.subject_name,
            func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present_c"),
            func.sum(case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent_c"),
        )
        .join(AttendanceSession, AttendanceSession.subject_id == Subject.id)
        .join(AttendanceRecord, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(AttendanceSession.status == SessionStatus.FINALIZED)
        .group_by(Subject.id, Subject.subject_code, Subject.subject_name)
        .limit(8)
    )
    subject_wise = []
    for row in res_subj_wise.all():
        p = row.present_c or 0
        a = row.absent_c or 0
        tot = p + a
        pct = round((p / tot * 100), 1) if tot > 0 else 0.0
        subject_wise.append({
            "subject_id": row.id,
            "subject_code": row.subject_code,
            "subject_name": row.subject_name,
            "present": p,
            "absent": a,
            "percentage": pct,
        })

    return {
        "summary": {
            "total_students": total_students,
            "total_teachers": total_lecturers,
            "total_classes": total_classes,
            "total_subjects": total_subjects,
            "total_sessions": total_sessions,
            "finalized_sessions": finalized_sessions,
            "draft_sessions": draft_sessions,
            "overall_percentage": overall_percentage,
            "sessions_today": sessions_today,
            "today_present": today_present,
            "today_absent": today_absent,
            "today_percentage": today_pct,
        },
        "trends": attendance_trends,
        "present_absent": [
            {"name": "Present", "value": total_present},
            {"name": "Absent", "value": total_absent},
        ],
        "class_wise": class_wise,
        "subject_wise": subject_wise,
        "recent_activity": recent_activity,
    }


# ---------------- Teacher Dashboard ----------------
@router.get("/teacher")
async def get_teacher_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_lecturer),
):
    """Aggregate live metrics and assigned classes for the teacher dashboard."""
    # Find teacher/lecturer record
    res_lec = await db.execute(select(Lecturer).where(Lecturer.user_id == current_user.id))
    lecturer = res_lec.scalar_one_or_none()
    if not lecturer:
        # Fallback if admin viewing
        res_first = await db.execute(select(Lecturer).limit(1))
        lecturer = res_first.scalar_one_or_none()

    if not lecturer:
        return {
            "summary": {
                "assigned_subjects": 0,
                "assigned_classes": 0,
                "total_students": 0,
                "total_sessions": 0,
                "finalized_sessions": 0,
                "draft_sessions": 0,
                "average_attendance": 0.0,
            },
            "assignments": [],
            "recent_sessions": [],
            "needs_review": [],
        }

    # Fetch teaching assignments
    res_asn = await db.execute(
        select(TeachingAssignment).where(TeachingAssignment.lecturer_id == lecturer.id)
    )
    assignments = res_asn.scalars().all()
    assigned_class_ids = list({a.class_id for a in assignments})
    assigned_subject_ids = list({a.subject_id for a in assignments})

    # Total students across assigned classes
    total_assigned_students = 0
    if assigned_class_ids:
        res_stu = await db.execute(
            select(func.count(Student.id)).where(
                Student.class_id.in_(assigned_class_ids), Student.is_active == True
            )
        )
        total_assigned_students = res_stu.scalar() or 0

    # Sessions conducted by this teacher
    res_sess = await db.execute(
        select(AttendanceSession).where(AttendanceSession.lecturer_id == lecturer.id)
    )
    teacher_sessions = res_sess.scalars().all()
    total_sessions = len(teacher_sessions)
    finalized_sessions = sum(1 for s in teacher_sessions if s.status == SessionStatus.FINALIZED)
    draft_sessions = sum(1 for s in teacher_sessions if s.status == SessionStatus.DRAFT)

    # Average attendance across teacher's finalized sessions
    res_avg = await db.execute(
        select(
            func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)),
            func.count(AttendanceRecord.id),
        )
        .join(AttendanceSession, AttendanceRecord.attendance_session_id == AttendanceSession.id)
        .where(
            AttendanceSession.lecturer_id == lecturer.id,
            AttendanceSession.status == SessionStatus.FINALIZED,
        )
    )
    row_avg = res_avg.one()
    p_cnt = row_avg[0] or 0
    tot_cnt = row_avg[1] or 0
    avg_pct = round((p_cnt / tot_cnt * 100), 1) if tot_cnt > 0 else 0.0

    # Build assignments detail
    assignments_list = []
    for a in assignments:
        subj = await db.get(Subject, a.subject_id)
        cls = await db.get(Class, a.class_id)
        assignments_list.append({
            "id": a.id,
            "class_id": a.class_id,
            "class_name": cls.name if cls else "Class",
            "subject_id": a.subject_id,
            "subject_name": subj.subject_name if subj else "Subject",
            "subject_code": subj.subject_code if subj else "",
            "semester": cls.semester if cls else 1,
        })

    # Recent sessions (latest 8)
    res_recent = await db.execute(
        select(AttendanceSession)
        .where(AttendanceSession.lecturer_id == lecturer.id)
        .order_by(AttendanceSession.attendance_date.desc(), AttendanceSession.id.desc())
        .limit(8)
    )
    recent_sessions = []
    needs_review = []
    for s in res_recent.scalars().all():
        subj = await db.get(Subject, s.subject_id)
        cls = await db.get(Class, s.class_id)
        item = {
            "id": s.id,
            "date": str(s.attendance_date),
            "period": s.period,
            "status": s.status.value,
            "source_type": s.source_type.value,
            "subject_name": subj.subject_name if subj else "Subject",
            "subject_code": subj.subject_code if subj else "",
            "class_name": cls.name if cls else "Class",
        }
        recent_sessions.append(item)
        if s.status == SessionStatus.DRAFT:
            needs_review.append(item)

    return {
        "teacher": {
            "id": lecturer.id,
            "name": lecturer.full_name,
            "employee_id": lecturer.employee_id,
        },
        "summary": {
            "assigned_subjects": len(assigned_subject_ids),
            "assigned_classes": len(assigned_class_ids),
            "total_students": total_assigned_students,
            "total_sessions": total_sessions,
            "finalized_sessions": finalized_sessions,
            "draft_sessions": draft_sessions,
            "average_attendance": avg_pct,
        },
        "assignments": assignments_list,
        "recent_sessions": recent_sessions,
        "needs_review": needs_review,
    }


# ---------------- Student Dashboard ----------------
@router.get("/student")
async def get_student_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_student),
):
    """Aggregate personal attendance data and subjects for the student dashboard."""
    res_stu = await db.execute(select(Student).where(Student.user_id == current_user.id))
    student = res_stu.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found for this account")

    cls = await db.get(Class, student.class_id)
    min_threshold_str = await get_setting(db, "min_attendance_percentage", str(settings.MIN_ATTENDANCE_PERCENTAGE))
    try:
        min_threshold = float(min_threshold_str)
    except ValueError:
        min_threshold = 75.0

    # Get all finalized sessions for this student's class
    res_sess = await db.execute(
        select(AttendanceSession)
        .where(
            AttendanceSession.class_id == student.class_id,
            AttendanceSession.status == SessionStatus.FINALIZED,
        )
        .order_by(AttendanceSession.attendance_date.desc(), AttendanceSession.period.desc())
    )
    sessions = res_sess.scalars().all()
    session_ids = [s.id for s in sessions]

    # Get student's records for these finalized sessions
    records_by_session = {}
    if session_ids:
        res_rec = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.attendance_session_id.in_(session_ids),
            )
        )
        for r in res_rec.scalars().all():
            records_by_session[r.attendance_session_id] = r

    # Aggregate by subject
    subjects_dict = {}
    total_conducted = 0
    total_attended = 0

    for s in sessions:
        if s.subject_id not in subjects_dict:
            subj = await db.get(Subject, s.subject_id)
            subjects_dict[s.subject_id] = {
                "subject_id": s.subject_id,
                "subject_name": subj.subject_name if subj else "Subject",
                "subject_code": subj.subject_code if subj else "",
                "conducted": 0,
                "attended": 0,
                "missed": 0,
            }

        rec = records_by_session.get(s.id)
        if rec:
            total_conducted += 1
            subjects_dict[s.subject_id]["conducted"] += 1
            if rec.status == AttendanceStatus.PRESENT:
                total_attended += 1
                subjects_dict[s.subject_id]["attended"] += 1
            else:
                subjects_dict[s.subject_id]["missed"] += 1

    subject_rows = []
    for s_info in subjects_dict.values():
        c = s_info["conducted"]
        a = s_info["attended"]
        pct = round((a / c * 100), 1) if c > 0 else 0.0
        subject_rows.append({
            **s_info,
            "percentage": pct,
            "is_shortage": pct < min_threshold if c > 0 else False,
        })

    overall_pct = round((total_attended / total_conducted * 100), 1) if total_conducted > 0 else 0.0
    total_missed = total_conducted - total_attended

    # Recent session records (latest 10)
    recent_history = []
    for s in sessions[:10]:
        rec = records_by_session.get(s.id)
        if rec:
            subj = await db.get(Subject, s.subject_id)
            recent_history.append({
                "record_id": rec.id,
                "session_id": s.id,
                "date": str(s.attendance_date),
                "period": s.period,
                "subject_name": subj.subject_name if subj else "Subject",
                "subject_code": subj.subject_code if subj else "",
                "status": rec.status.value,
                "is_corrected": rec.is_corrected,
            })

    return {
        "student": {
            "id": student.id,
            "usn": student.usn,
            "full_name": student.full_name,
            "class_name": cls.name if cls else "N/A",
            "semester": student.semester,
            "academic_year": student.academic_year,
        },
        "summary": {
            "overall_percentage": overall_pct,
            "total_conducted": total_conducted,
            "total_attended": total_attended,
            "total_missed": total_missed,
            "min_threshold": min_threshold,
            "has_shortage": overall_pct < min_threshold if total_conducted > 0 else False,
        },
        "subjects": subject_rows,
        "recent_history": recent_history,
    }
