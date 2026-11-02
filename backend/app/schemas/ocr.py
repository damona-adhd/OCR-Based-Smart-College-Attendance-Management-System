from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class AttendanceMarkStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    UNKNOWN = "unknown"


class MatchStatus(str, Enum):
    MATCHED = "matched"
    UNMATCHED = "unmatched"
    UNCERTAIN = "uncertain"
    AMBIGUOUS = "ambiguous"
    DUPLICATE = "duplicate"
    MISSING = "missing"


class OCRRowResult(BaseModel):
    page_number: int = 1
    row_index: int
    student_name: Optional[str] = None
    usn: Optional[str] = None
    raw_attendance_mark: Optional[str] = None
    attendance_status: AttendanceMarkStatus = AttendanceMarkStatus.UNKNOWN
    match_status: MatchStatus = MatchStatus.UNMATCHED
    confidence: Optional[float] = 0.0
    review_required: bool = True
    review_reason: Optional[str] = None

    # Matched DB fields
    matched_student_id: Optional[int] = None
    matched_student_name: Optional[str] = None
    matched_student_usn: Optional[str] = None

    # Backward compatibility aliases
    extracted_usn: Optional[str] = None
    extracted_name: Optional[str] = None
    proposed_status: Optional[str] = None
    needs_review: bool = True
    corrected_student_id: Optional[int] = None
    corrected_status: Optional[str] = None


class OCRProcessingResult(BaseModel):
    source_file_id: int
    session_id: int
    extraction_provider: str = "auto"
    processing_status: str = "completed"
    page_count: int = 1
    rows: List[OCRRowResult] = Field(default_factory=list)
    total_candidate_rows: int = 0
    valid_rows: int = 0
    matched_students: int = 0
    unmatched_students: int = 0
    ambiguous_rows: int = 0
    present_count: int = 0
    absent_count: int = 0
    unknown_count: int = 0

    # Backward compatibility counts
    total_extracted: int = 0
    total_matched: int = 0
    total_unmatched: int = 0
    total_uncertain: int = 0
    processing_note: Optional[str] = None
    provider_errors: List[str] = Field(default_factory=list)


class OCRCorrectionRow(BaseModel):
    row_index: int
    student_id: Optional[int] = None
    attendance_status: str  # "present" | "absent"


class OCRConfirmRequest(BaseModel):
    session_id: int
    corrections: List[OCRCorrectionRow]
