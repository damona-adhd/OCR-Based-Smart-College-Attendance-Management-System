"""
Extraction orchestrator: coordinates provider selection, fallback strategy,
and database class-roster matching.
"""
import re
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.student import Student
from app.schemas.ocr import OCRProcessingResult, OCRRowResult, MatchStatus, AttendanceMarkStatus
from app.services.extraction.base import (
    BaseExtractionProvider,
    CandidateRow,
    ExtractionDocumentResult,
    AttendanceMarkStatus as ExtMarkStatus,
    MatchStatus as ExtMatchStatus,
)
from app.services.extraction.pymupdf_provider import PyMuPDFExtractionProvider
from app.services.extraction.gemini_provider import GeminiExtractionProvider
from app.services.extraction.tesseract_provider import TesseractExtractionProvider

logger = logging.getLogger(__name__)


def normalize_usn(raw: Optional[str]) -> str:
    if not raw:
        return ""
    return re.sub(r"[^A-Z0-9]", "", raw.upper())


class ExtractionOrchestrator:
    def __init__(self):
        self.pymupdf_provider = PyMuPDFExtractionProvider()
        self.gemini_provider = GeminiExtractionProvider()
        self.tesseract_provider = TesseractExtractionProvider()

    async def process_document(
        self,
        db: AsyncSession,
        file_path: str,
        mime_type: str,
        session_id: int,
        source_file_id: int,
        class_id: int,
        forced_provider: Optional[str] = None,
    ) -> OCRProcessingResult:
        """
        Main entry point for document extraction with automatic provider routing
        and full roster matching.
        """
        provider_name = forced_provider or settings.ATTENDANCE_EXTRACTION_PROVIDER or "auto"
        is_pdf = file_path.lower().endswith(".pdf") or mime_type == "application/pdf"

        raw_result: Optional[ExtractionDocumentResult] = None
        selected_provider_used = "unknown"
        provider_errors: List[str] = []

        logger.info(
            "ExtractionOrchestrator: start file=%s mime=%s strategy=%s",
            file_path, mime_type, provider_name,
        )

        # 1. Forced provider logic
        if provider_name == "gemini":
            selected_provider_used = "gemini"
            raw_result = await self.gemini_provider.extract(file_path, mime_type)
        elif provider_name == "pymupdf":
            selected_provider_used = "pymupdf"
            raw_result = await self.pymupdf_provider.extract(file_path, mime_type)
        elif provider_name == "tesseract":
            selected_provider_used = "tesseract"
            raw_result = await self.tesseract_provider.extract(file_path, mime_type)
        else:
            # AUTO STRATEGY:
            # Step A: If PDF, test digital text extraction first
            if is_pdf:
                logger.info("Auto Strategy: testing PyMuPDF direct text/table extraction")
                pdf_res = await self.pymupdf_provider.extract(file_path, mime_type)
                if pdf_res.status == "success" and len(pdf_res.rows) > 0:
                    logger.info("Auto Strategy: PyMuPDF succeeded with %d rows", len(pdf_res.rows))
                    raw_result = pdf_res
                    selected_provider_used = "pymupdf"
                else:
                    if pdf_res.errors:
                        provider_errors.extend(pdf_res.errors)
                    logger.info(
                        "Auto Strategy: PyMuPDF reported '%s'. Falling back to vision/OCR.",
                        pdf_res.status,
                    )

            # Step B: If not resolved yet (scanned PDF or image), prefer Gemini Vision if API key is present
            if not raw_result or raw_result.status != "success":
                if settings.GEMINI_API_KEY:
                    logger.info("Auto Strategy: invoking Gemini Vision provider")
                    gemini_res = await self.gemini_provider.extract(file_path, mime_type)
                    if gemini_res.status == "success" and len(gemini_res.rows) > 0:
                        raw_result = gemini_res
                        selected_provider_used = "gemini"
                    else:
                        if gemini_res.errors:
                            provider_errors.extend(gemini_res.errors)
                        logger.warning("Auto Strategy: Gemini extraction returned '%s'. Trying Tesseract fallback.", gemini_res.status)

            # Step C: Fallback to Tesseract OCR
            if not raw_result or raw_result.status != "success":
                logger.info("Auto Strategy: invoking Tesseract OCR fallback")
                tess_res = await self.tesseract_provider.extract(file_path, mime_type)
                selected_provider_used = "tesseract"
                raw_result = tess_res
                if tess_res.errors:
                    provider_errors.extend(tess_res.errors)

        if not raw_result:
            raw_result = ExtractionDocumentResult(
                provider=selected_provider_used,
                status="failed",
                errors=["No extraction provider was able to process this file."],
            )

        # 2. Match candidate rows against class roster
        roster_students = await self._get_class_roster(db, class_id)
        matched_result = self._match_roster(
            candidate_rows=raw_result.rows,
            roster=roster_students,
            source_file_id=source_file_id,
            session_id=session_id,
            provider_used=selected_provider_used,
            provider_note=raw_result.notes,
            provider_errors=provider_errors + raw_result.errors,
            page_count=raw_result.page_count,
        )

        return matched_result

    async def _get_class_roster(self, db: AsyncSession, class_id: int) -> List[Student]:
        result = await db.execute(
            select(Student).where(Student.class_id == class_id, Student.is_active == True)
        )
        return result.scalars().all()

    def _match_roster(
        self,
        candidate_rows: List[CandidateRow],
        roster: List[Student],
        source_file_id: int,
        session_id: int,
        provider_used: str,
        provider_note: Optional[str],
        provider_errors: List[str],
        page_count: int,
    ) -> OCRProcessingResult:
        """
        Matches extracted candidate rows to real database student records.
        Preserves ALL candidate rows even if 0 students exist in the class.
        """
        roster_map = {normalize_usn(s.usn): s for s in roster}
        seen_usns: Dict[str, int] = {}
        result_rows: List[OCRRowResult] = []
        matched_student_ids: set = set()

        for idx, cand in enumerate(candidate_rows):
            norm_usn = normalize_usn(cand.usn)
            student = roster_map.get(norm_usn) if norm_usn else None

            match_status = MatchStatus.UNMATCHED
            matched_id = None
            matched_name = None
            matched_usn = None
            needs_review = True
            reason = cand.review_reason

            if not roster:
                # Class has no enrolled students — preserve row but flag review
                match_status = MatchStatus.UNMATCHED
                needs_review = True
                reason = "No students enrolled in this class to match against"
            elif norm_usn and norm_usn in seen_usns:
                # Duplicate entry in document
                match_status = MatchStatus.DUPLICATE
                matched_id = student.id if student else None
                matched_name = student.full_name if student else None
                matched_usn = student.usn if student else None
                needs_review = True
                reason = f"Duplicate USN {norm_usn} observed in document"
            elif student:
                # Exact USN match
                seen_usns[norm_usn] = idx
                matched_id = student.id
                matched_name = student.full_name
                matched_usn = student.usn
                matched_student_ids.add(student.id)

                if cand.attendance_status != ExtMarkStatus.UNKNOWN:
                    match_status = MatchStatus.MATCHED
                    needs_review = False
                    reason = None
                else:
                    match_status = MatchStatus.MATCHED
                    needs_review = True
                    reason = "Attendance mark unclear — verify present or absent"
            else:
                # Try name fuzzy matching if student name exists
                name_match, is_ambiguous = self._fuzzy_match_name(cand.student_name, roster)
                if name_match:
                    matched_id = name_match.id
                    matched_name = name_match.full_name
                    matched_usn = name_match.usn
                    matched_student_ids.add(name_match.id)
                    if is_ambiguous:
                        match_status = MatchStatus.AMBIGUOUS
                        reason = "Multiple students have similar names"
                    else:
                        match_status = MatchStatus.UNCERTAIN
                        reason = f"Matched by student name ({name_match.full_name}); USN differs or was missing"
                    needs_review = True
                else:
                    match_status = MatchStatus.UNMATCHED
                    needs_review = True
                    reason = "USN and name not found in enrolled class roster"

            # Attendance status conversion
            schema_status = AttendanceMarkStatus(cand.attendance_status.value)
            prop_status = cand.attendance_status.value if cand.attendance_status != ExtMarkStatus.UNKNOWN else None

            row_out = OCRRowResult(
                page_number=cand.page_number,
                row_index=cand.row_index or (idx + 1),
                student_name=cand.student_name,
                usn=cand.usn,
                raw_attendance_mark=cand.raw_attendance_mark,
                attendance_status=schema_status,
                match_status=match_status,
                confidence=round(cand.confidence * 100, 1) if cand.confidence else 0.0,
                review_required=needs_review,
                review_reason=reason,
                matched_student_id=matched_id,
                matched_student_name=matched_name,
                matched_student_usn=matched_usn,
                # Backward compatibility
                extracted_usn=cand.usn,
                extracted_name=cand.student_name,
                proposed_status=prop_status,
                needs_review=needs_review,
                corrected_student_id=matched_id,
                corrected_status=prop_status or "absent",
            )
            result_rows.append(row_out)

        # Add missing enrolled students (on roster but not found in document)
        if roster:
            for s in roster:
                if s.id not in matched_student_ids:
                    result_rows.append(
                        OCRRowResult(
                            page_number=1,
                            row_index=9000 + s.id,
                            student_name=s.full_name,
                            usn=s.usn,
                            raw_attendance_mark=None,
                            attendance_status=AttendanceMarkStatus.UNKNOWN,
                            match_status=MatchStatus.MISSING,
                            confidence=0.0,
                            review_required=True,
                            review_reason="Enrolled student was not found in the uploaded attendance register",
                            matched_student_id=s.id,
                            matched_student_name=s.full_name,
                            matched_student_usn=s.usn,
                            extracted_usn=None,
                            extracted_name=None,
                            proposed_status=None,
                            needs_review=True,
                            corrected_student_id=s.id,
                            corrected_status="absent",
                        )
                    )

        # Recalculate summary metrics from validated row data
        cand_count = len(candidate_rows)
        matched_count = sum(1 for r in result_rows if r.match_status == MatchStatus.MATCHED)
        unmatched_count = sum(1 for r in result_rows if r.match_status == MatchStatus.UNMATCHED)
        ambiguous_count = sum(1 for r in result_rows if r.match_status in (MatchStatus.AMBIGUOUS, MatchStatus.UNCERTAIN))
        present_count = sum(1 for r in result_rows if r.attendance_status == AttendanceMarkStatus.PRESENT)
        absent_count = sum(1 for r in result_rows if r.attendance_status == AttendanceMarkStatus.ABSENT)
        unknown_count = sum(1 for r in result_rows if r.attendance_status == AttendanceMarkStatus.UNKNOWN)

        # Detailed processing note
        note_parts = []
        if provider_note:
            note_parts.append(provider_note)
        else:
            note_parts.append(f"Processed via provider '{provider_used}' across {page_count} page(s).")

        if not roster:
            note_parts.append(
                "Notice: No students are currently enrolled in this class. "
                "Candidate rows from the document are preserved above. Please add or assign students to finalize."
            )
        elif unmatched_count > 0:
            note_parts.append(f"{unmatched_count} extracted rows did not match the enrolled class roster.")

        final_note = " ".join(note_parts)

        return OCRProcessingResult(
            source_file_id=source_file_id,
            session_id=session_id,
            extraction_provider=provider_used,
            processing_status="completed",
            page_count=page_count,
            rows=result_rows,
            total_candidate_rows=cand_count,
            valid_rows=len(result_rows),
            matched_students=matched_count,
            unmatched_students=unmatched_count,
            ambiguous_rows=ambiguous_count,
            present_count=present_count,
            absent_count=absent_count,
            unknown_count=unknown_count,
            # Backward compatibility aliases
            total_extracted=cand_count,
            total_matched=matched_count,
            total_unmatched=unmatched_count,
            total_uncertain=ambiguous_count,
            processing_note=final_note,
            provider_errors=provider_errors,
        )

    def _fuzzy_match_name(self, extracted_name: Optional[str], roster: List[Student]):
        """Match extracted name against roster students."""
        if not extracted_name or len(extracted_name.strip()) < 3:
            return None, False

        clean_ext = re.sub(r"[^A-Za-z]", "", extracted_name.lower())
        candidates = []

        for s in roster:
            clean_s = re.sub(r"[^A-Za-z]", "", s.full_name.lower())
            if clean_ext == clean_s:
                return s, False
            if clean_ext in clean_s or clean_s in clean_ext:
                candidates.append(s)

        if len(candidates) == 1:
            return candidates[0], False
        elif len(candidates) > 1:
            return candidates[0], True
        return None, False


extraction_orchestrator = ExtractionOrchestrator()
