from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.models.attendance_session import SessionStatus, SourceType
from app.models.attendance_record import AttendanceStatus


# ---- Session Schemas ----

class SessionCreate(BaseModel):
    subject_id: int
    class_id: int
    attendance_date: date
    source_type: SourceType = SourceType.MANUAL


class SessionUpdate(BaseModel):
    attendance_date: Optional[date] = None
    status: Optional[SessionStatus] = None


class AttendanceRecordIn(BaseModel):
    student_id: int
    status: AttendanceStatus


class SessionOut(BaseModel):
    id: int
    subject_id: int
    class_id: int
    lecturer_id: int
    attendance_date: date
    status: SessionStatus
    source_type: SourceType
    source_file_id: Optional[int] = None
    finalized_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionDetailOut(SessionOut):
    records: List["AttendanceRecordOut"] = []
    subject_name: Optional[str] = None
    class_name: Optional[str] = None
    lecturer_name: Optional[str] = None


# ---- Record Schemas ----

class AttendanceRecordOut(BaseModel):
    id: int
    attendance_session_id: int
    student_id: int
    status: AttendanceStatus
    source_type: SourceType
    student_usn: Optional[str] = None
    student_name: Optional[str] = None

    model_config = {"from_attributes": True}


# ---- Manual Attendance ----

class ManualAttendanceSubmit(BaseModel):
    records: List[AttendanceRecordIn]


class FinalizeSession(BaseModel):
    confirm: bool = True


class CancelSession(BaseModel):
    reason: str


# ---- Correction after finalization ----

class AttendanceCorrectionRequest(BaseModel):
    student_id: int
    new_status: AttendanceStatus
    reason: str


SessionDetailOut.model_rebuild()
