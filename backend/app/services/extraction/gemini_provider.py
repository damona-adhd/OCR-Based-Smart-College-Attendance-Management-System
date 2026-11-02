"""
Gemini Vision-Language Model provider for scanned and handwritten attendance sheets.
Uses the official google-genai SDK with strict JSON output formatting.
"""
import os
import json
import re
import logging
from typing import Optional, List, Dict, Any

from app.core.config import settings
from app.services.extraction.base import (
    BaseExtractionProvider,
    CandidateRow,
    ExtractionDocumentResult,
    AttendanceMarkStatus,
    MatchStatus,
)
from app.services.extraction.pymupdf_provider import PyMuPDFExtractionProvider

logger = logging.getLogger(__name__)


class GeminiExtractionProvider(BaseExtractionProvider):
    @property
    def name(self) -> str:
        return "gemini"

    async def extract(
        self,
        file_path: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ExtractionDocumentResult:
        if not settings.GEMINI_API_KEY:
            logger.warning("GeminiExtractionProvider: GEMINI_API_KEY is not set.")
            return ExtractionDocumentResult(
                provider=self.name,
                status="unconfigured",
                errors=[
                    "GEMINI_API_KEY is not configured in backend environment. "
                    "Please configure your Google Gemini API key to enable vision extraction on handwritten sheets."
                ],
            )

        if not os.path.exists(file_path):
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"File not found: {file_path}"],
            )

        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            model_name = settings.GEMINI_MODEL or "gemini-2.5-flash"

            is_pdf = file_path.lower().endswith(".pdf") or mime_type == "application/pdf"
            page_images_bytes: List[bytes] = []

            if is_pdf:
                logger.info("Gemini: rendering PDF pages to high-res images with PyMuPDF")
                page_images_bytes = PyMuPDFExtractionProvider.render_pdf_to_images(file_path, dpi=300)
            else:
                with open(file_path, "rb") as f:
                    page_images_bytes = [f.read()]

            if not page_images_bytes:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="failed",
                    errors=["Failed to obtain page images from the document."],
                )

            all_candidate_rows: List[CandidateRow] = []
            global_row_idx = 0

            prompt = (
                "You are an expert document analysis system for college student attendance registers and ledgers.\n"
                "Examine this attendance sheet image carefully.\n"
                "Extract every student row in the register table.\n"
                "For each student row, extract:\n"
                "- row_index: row or serial number (integer)\n"
                "- student_name: full student name (string, or null if completely unreadable)\n"
                "- usn: University Seat Number / student identifier (string, or null if unreadable)\n"
                "- raw_attendance_mark: exact symbol or character observed (e.g. 'P', 'A', '✓', '✗', etc.)\n"
                "- attendance_status: 'present' if marked present, 'absent' if marked absent, 'unknown' if ambiguous or illegible\n"
                "- review_reason: brief explanation if handwriting or mark is ambiguous, else null\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. Distinguish header rows (Roll No, USN, Subject, Faculty) from actual student rows.\n"
                "2. Extract names and USNs ONLY when supported by visible evidence in the sheet. Do NOT invent students.\n"
                "3. If an attendance mark is unclear, ambiguous, or smudged, set attendance_status to 'unknown'. Do NOT guess.\n"
                "4. If there are multiple date columns, extract the latest / last attendance column for each student.\n"
                "5. Return strictly valid JSON in the format: {\"rows\": [...]}\n"
            )

            for page_idx, img_bytes in enumerate(page_images_bytes, start=1):
                logger.info("Gemini: analyzing page %d/%d with model %s", page_idx, len(page_images_bytes), model_name)

                # Determine image format
                part_mime = "image/png" if is_pdf or file_path.lower().endswith(".png") else "image/jpeg"
                img_part = types.Part.from_bytes(data=img_bytes, mime_type=part_mime)

                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, img_part],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )

                response_text = response.text or "{}"
                page_rows = self._parse_gemini_json(response_text, page_idx, global_row_idx)
                for r in page_rows:
                    global_row_idx += 1
                    r.row_index = global_row_idx
                    all_candidate_rows.append(r)

            if not all_candidate_rows:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="failed",
                    page_count=len(page_images_bytes),
                    errors=["Gemini vision model processed the document but found 0 candidate student rows."],
                )

            # Recalculate summary stats on backend
            present = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.PRESENT)
            absent = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.ABSENT)
            unknown = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.UNKNOWN)

            return ExtractionDocumentResult(
                provider=self.name,
                status="success",
                page_count=len(page_images_bytes),
                rows=all_candidate_rows,
                total_candidate_rows=len(all_candidate_rows),
                valid_rows=len(all_candidate_rows),
                present_count=present,
                absent_count=absent,
                unknown_count=unknown,
                notes=(
                    f"Gemini Vision successfully interpreted {len(all_candidate_rows)} student rows across "
                    f"{len(page_images_bytes)} page(s)."
                ),
            )

        except Exception as e:
            logger.exception("GeminiExtractionProvider error: %s", e)
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"Gemini API error: {str(e)}"],
            )

    def _parse_gemini_json(self, raw_text: str, page_num: int, start_idx: int) -> List[CandidateRow]:
        """Safely parse Gemini JSON response into CandidateRow objects."""
        # Strip potential markdown fences
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON substring
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(1))
                except Exception:
                    data = {}
            else:
                data = {}

        items = data.get("rows", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        results: List[CandidateRow] = []

        for idx, item in enumerate(items, start=start_idx + 1):
            if not isinstance(item, dict):
                continue

            name = item.get("student_name")
            usn = item.get("usn")
            raw_mark = str(item.get("raw_attendance_mark") or "")
            raw_status = str(item.get("attendance_status") or "").lower()

            status = AttendanceMarkStatus.UNKNOWN
            if raw_status in ("present", "p"):
                status = AttendanceMarkStatus.PRESENT
            elif raw_status in ("absent", "a"):
                status = AttendanceMarkStatus.ABSENT

            review_reason = item.get("review_reason")
            if status == AttendanceMarkStatus.UNKNOWN and not review_reason:
                review_reason = "Attendance mark unclear or missing"

            # Filter out non-student rows
            if not usn and not name:
                continue
            if name and any(h in name.lower() for h in ["roll no", "usn / sr", "student name", "faculty"]):
                continue

            results.append(
                CandidateRow(
                    page_number=page_num,
                    row_index=idx,
                    student_name=name.strip() if name else None,
                    usn=usn.strip().upper() if usn else None,
                    raw_attendance_mark=raw_mark if raw_mark else None,
                    attendance_status=status,
                    match_status=MatchStatus.UNMATCHED,
                    confidence=0.95,
                    review_required=(status == AttendanceMarkStatus.UNKNOWN or not usn),
                    review_reason=review_reason,
                )
            )

        return results
