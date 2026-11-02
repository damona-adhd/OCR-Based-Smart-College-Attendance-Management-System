"""
Tesseract OCR extraction provider with OpenCV preprocessing and grid detection.
Used as fallback when Gemini API key is not configured or offline.
"""
import os
import re
import logging
from typing import Optional, List, Dict, Any
import numpy as np

from app.core.config import settings
from app.services.extraction.base import (
    BaseExtractionProvider,
    CandidateRow,
    ExtractionDocumentResult,
    AttendanceMarkStatus,
    MatchStatus,
)
from app.services.extraction.opencv_grid import OpenCVGridDetector
from app.services.extraction.pymupdf_provider import PyMuPDFExtractionProvider

logger = logging.getLogger(__name__)

USN_PATTERN = re.compile(
    r"\b\d{1,2}[A-Z]{2,4}\d{2}[A-Z]{1,3}\d{3}\b"
    r"|\b0[12]JST\w{6,10}\b"
    r"|\b[A-Z0-9]{8,15}\b",
    re.IGNORECASE,
)


class TesseractExtractionProvider(BaseExtractionProvider):
    @property
    def name(self) -> str:
        return "tesseract"

    async def extract(
        self,
        file_path: str,
        mime_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> ExtractionDocumentResult:
        if not os.path.exists(file_path):
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"File not found: {file_path}"],
            )

        try:
            import pytesseract
            import cv2
            tess_cmd = settings.resolved_tesseract_cmd
            pytesseract.pytesseract.tesseract_cmd = tess_cmd
        except ImportError as e:
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"pytesseract or OpenCV is not installed: {e}"],
            )

        is_pdf = file_path.lower().endswith(".pdf") or mime_type == "application/pdf"
        page_images: List[np.ndarray] = []

        try:
            if is_pdf:
                # Use PyMuPDF to render pages to images
                raw_bytes_list = PyMuPDFExtractionProvider.render_pdf_to_images(file_path, dpi=300)
                for b in raw_bytes_list:
                    arr = np.frombuffer(b, dtype=np.uint8)
                    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img is not None:
                        page_images.append(img)
            else:
                img = cv2.imread(file_path)
                if img is not None:
                    page_images.append(img)

            if not page_images:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="failed",
                    errors=["Could not load or decode image from file."],
                )

            all_candidate_rows: List[CandidateRow] = []
            global_row_idx = 0

            for page_idx, page_img in enumerate(page_images, start=1):
                preprocessed = OpenCVGridDetector.preprocess_for_ocr(page_img)

                # Try OpenCV table grid detection if enabled
                grid_info = (
                    OpenCVGridDetector.detect_table_grid(page_img)
                    if settings.ENABLE_OPENCV_GRID_DETECTION
                    else {"has_grid": False, "row_boxes": []}
                )

                page_rows = []
                if grid_info.get("has_grid") and grid_info.get("row_boxes"):
                    logger.info("Tesseract: page %d detected %d table row regions", page_idx, len(grid_info["row_boxes"]))
                    for box_idx, (rx, ry, rw, rh) in enumerate(grid_info["row_boxes"]):
                        row_crop = preprocessed[ry : ry + rh, rx : rx + rw]
                        if row_crop.size == 0:
                            continue
                        text = pytesseract.image_to_string(row_crop, config="--psm 6")
                        cand = self._parse_ocr_line(text, page_idx, global_row_idx + 1)
                        if cand:
                            global_row_idx += 1
                            cand.row_index = global_row_idx
                            page_rows.append(cand)

                # Fallback to full page PSM 6 line parsing if grid detection didn't yield rows
                if not page_rows:
                    logger.info("Tesseract: running full page OCR on page %d", page_idx)
                    full_text = pytesseract.image_to_string(preprocessed, config="--psm 6")
                    for line in full_text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        cand = self._parse_ocr_line(line, page_idx, global_row_idx + 1)
                        if cand:
                            global_row_idx += 1
                            cand.row_index = global_row_idx
                            page_rows.append(cand)

                all_candidate_rows.extend(page_rows)

            if not all_candidate_rows:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="failed",
                    page_count=len(page_images),
                    errors=[
                        "Tesseract OCR processed the document but found no candidate student rows. "
                        "Tips: Ensure high resolution (300 DPI), flat lighting, and clearly printed USNs. "
                        "You can also use Manual Attendance Entry."
                    ],
                )

            present = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.PRESENT)
            absent = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.ABSENT)
            unknown = sum(1 for r in all_candidate_rows if r.attendance_status == AttendanceMarkStatus.UNKNOWN)

            return ExtractionDocumentResult(
                provider=self.name,
                status="success",
                page_count=len(page_images),
                rows=all_candidate_rows,
                total_candidate_rows=len(all_candidate_rows),
                valid_rows=len(all_candidate_rows),
                present_count=present,
                absent_count=absent,
                unknown_count=unknown,
                notes=f"Tesseract OCR extracted {len(all_candidate_rows)} student rows across {len(page_images)} page(s).",
            )

        except Exception as e:
            logger.exception("Tesseract extraction error: %s", e)
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"Tesseract OCR processing failed: {str(e)}"],
            )

    def _parse_ocr_line(self, line: str, page_num: int, default_idx: int) -> Optional[CandidateRow]:
        """Examine OCR text and extract USN, student name, and attendance mark."""
        m = USN_PATTERN.search(line)
        if not m:
            return None
        usn_token = m.group(0).upper().replace("O", "0")
        if not (any(c.isdigit() for c in usn_token) and any(c.isalpha() for c in usn_token)):
            return None

        # Attendance mark: P or A
        mark_val = None
        status = AttendanceMarkStatus.UNKNOWN
        if re.search(r"\b[PA]\b", line):
            marks = re.findall(r"\b([PA])\b", line)
            mark_val = marks[-1]
            status = AttendanceMarkStatus.PRESENT if mark_val == "P" else AttendanceMarkStatus.ABSENT
        elif " P " in line or line.endswith(" P") or "|P" in line or "P|" in line:
            mark_val = "P"
            status = AttendanceMarkStatus.PRESENT
        elif " A " in line or line.endswith(" A") or "|A" in line or "A|" in line:
            mark_val = "A"
            status = AttendanceMarkStatus.ABSENT

        # Student Name extraction
        line_clean = line.replace(m.group(0), "")
        words = re.findall(r"[A-Za-z]{2,}", line_clean)
        # Filter headers
        words = [w for w in words if w.lower() not in ("roll", "no", "usn", "sr", "name", "student", "faculty", "signature")]
        name_val = " ".join(words) if words else None

        return CandidateRow(
            page_number=page_num,
            row_index=default_idx,
            student_name=name_val,
            usn=usn_token,
            raw_attendance_mark=mark_val,
            attendance_status=status,
            match_status=MatchStatus.UNMATCHED,
            confidence=0.75,
            review_required=(status == AttendanceMarkStatus.UNKNOWN),
            review_reason="Attendance mark unclear" if status == AttendanceMarkStatus.UNKNOWN else None,
        )
