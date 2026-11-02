"""
Document extraction package for Smart College Attendance Management System.
Supports:
- Gemini Vision-Language Model (scanned / handwritten registers)
- PyMuPDF Direct Table Extraction (digital PDFs)
- OpenCV Grid & Table Border Detection
- Tesseract OCR (fallback)
"""
from app.services.extraction.base import (
    BaseExtractionProvider,
    CandidateRow,
    ExtractionDocumentResult,
    AttendanceMarkStatus,
    MatchStatus,
)
from app.services.extraction.orchestrator import ExtractionOrchestrator, extraction_orchestrator

__all__ = [
    "BaseExtractionProvider",
    "CandidateRow",
    "ExtractionDocumentResult",
    "AttendanceMarkStatus",
    "MatchStatus",
    "ExtractionOrchestrator",
    "extraction_orchestrator",
]
