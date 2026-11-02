from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class SubjectAttendanceSummary(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float
    is_shortage: bool


class StudentAttendanceReport(BaseModel):
    student_id: int
    usn: str
    full_name: str
    subjects: List[SubjectAttendanceSummary]
    overall_percentage: float


class ClassAttendanceRow(BaseModel):
    student_id: int
    usn: str
    full_name: str
    attended: int
    total: int
    percentage: float
    is_shortage: bool


class ClassAttendanceReport(BaseModel):
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    date_from: Optional[date]
    date_to: Optional[date]
    rows: List[ClassAttendanceRow]


class DailyAttendanceRow(BaseModel):
    attendance_date: date
    subject_code: str
    subject_name: str
    class_name: str
    present_count: int
    absent_count: int
    total_count: int
    attendance_percentage: float


class AuditEventOut(BaseModel):
    id: int
    actor_user_id: Optional[int]
    actor_username: Optional[str]
    action: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    details: Optional[dict]
    created_at: str

    model_config = {"from_attributes": True}
