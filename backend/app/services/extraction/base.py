"""
Common interface and schemas for attendance document extraction providers.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


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


class CandidateRow(BaseModel):
    page_number: int = 1
    row_index: int = 0
    student_name: Optional[str] = None
    usn: Optional[str] = None
    raw_attendance_mark: Optional[str] = None
    attendance_status: AttendanceMarkStatus = AttendanceMarkStatus.UNKNOWN
    match_status: MatchStatus = MatchStatus.UNMATCHED
    confidence: Optional[float] = None  # None or 0.0 - 1.0 (or 0 - 100)
    review_required: bool = True
    review_reason: Optional[str] = None

    # Database matching fields
    matched_student_id: Optional[int] = None
    matched_student_name: Optional[str] = None
    matched_student_usn: Optional[str] = None

    # Backward compatibility helpers
    @property
    def extracted_usn(self) -> Optional[str]:
        return self.usn

    @property
    def extracted_name(self) -> Optional[str]:
        return self.student_name

    @property
    def proposed_status(self) -> Optional[str]:
        if self.attendance_status == AttendanceMarkStatus.PRESENT:
            return "present"
        if self.attendance_status == AttendanceMarkStatus.ABSENT:
            return "absent"
        return None


class ExtractionDocumentResult(BaseModel):
    provider: str
    status: str = "success"  # success | partial | failed | insufficient_text | unconfigured
    page_count: int = 1
    rows: List[CandidateRow] = Field(default_factory=list)
    total_candidate_rows: int = 0
    valid_rows: int = 0
    matched_students: int = 0
    unmatched_students: int = 0
    ambiguous_rows: int = 0
    present_count: int = 0
    absent_count: int = 0
    unknown_count: int = 0
    notes: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class BaseExtractionProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'gemini', 'pymupdf', 'tesseract')."""
        pass

    @abstractmethod
    async def extract(
        self,
        file_path: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ExtractionDocumentResult:
        """
        Extract attendance candidate rows from a document (PDF or image).
        Must never write directly to official attendance tables.
        """
        pass
