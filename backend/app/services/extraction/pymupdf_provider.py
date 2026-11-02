"""
PyMuPDF direct extraction provider for digital PDFs with selectable text/tables.
Does not require external OCR or API keys.
"""
import os
import re
import logging
from typing import Optional, List, Dict, Any
import pymupdf

from app.services.extraction.base import (
    BaseExtractionProvider,
    CandidateRow,
    ExtractionDocumentResult,
    AttendanceMarkStatus,
    MatchStatus,
)

logger = logging.getLogger(__name__)

# USN patterns: e.g. 1CS21CS001, 01JST24UCS007, 02JST24UCS002, VTU21CS001, etc.
USN_REGEX = re.compile(
    r"\b\d{1,2}[A-Z]{2,4}\d{2}[A-Z]{1,3}\d{3}\b"
    r"|\b0[12]JST\w{6,10}\b"
    r"|\b[A-Z0-9]{8,15}\b",
    re.IGNORECASE,
)


class PyMuPDFExtractionProvider(BaseExtractionProvider):
    @property
    def name(self) -> str:
        return "pymupdf"

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

        if not file_path.lower().endswith(".pdf") and mime_type != "application/pdf":
            return ExtractionDocumentResult(
                provider=self.name,
                status="insufficient_text",
                errors=["PyMuPDF direct table extraction only supports PDF documents."],
            )

        try:
            doc = pymupdf.open(file_path)
            page_count = len(doc)
            if page_count == 0:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="failed",
                    errors=["PDF document contains 0 pages."],
                )

            # Check digital text layer across document
            total_text_len = 0
            for page in doc:
                total_text_len += len(page.get_text().strip())

            logger.info("PyMuPDF: page_count=%d, total_text_len=%d", page_count, total_text_len)

            if total_text_len < 40:
                # Scanned image PDF without digital text layer
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="insufficient_text",
                    page_count=page_count,
                    notes="PDF contains scanned page images without a selectable text layer. Routing to vision/OCR provider.",
                )

            candidate_rows: List[CandidateRow] = []
            row_counter = 0

            for page_idx, page in enumerate(doc, start=1):
                page_extracted = False
                # 1. Try PyMuPDF find_tables()
                try:
                    table_finder = page.find_tables()
                    tables = table_finder.tables if hasattr(table_finder, "tables") else []
                    for tab in tables:
                        tab_data = tab.extract()
                        for row_data in tab_data:
                            cleaned_cells = [
                                re.sub(r"\s+", " ", (c or "")).strip() for c in row_data
                            ]
                            cand = self._parse_table_row(cleaned_cells, page_idx, row_counter + 1)
                            if cand:
                                row_counter += 1
                                cand.row_index = row_counter
                                candidate_rows.append(cand)
                                page_extracted = True
                except Exception as ex:
                    logger.warning("PyMuPDF find_tables failed on page %d: %s", page_idx, ex)

                # 2. If table finding didn't extract rows on this page, fall back to line text parsing
                if not page_extracted:
                    lines = page.get_text("text").splitlines()
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        cand = self._parse_text_line(line, page_idx, row_counter + 1)
                        if cand:
                            row_counter += 1
                            cand.row_index = row_counter
                            candidate_rows.append(cand)

            if not candidate_rows:
                return ExtractionDocumentResult(
                    provider=self.name,
                    status="insufficient_text",
                    page_count=page_count,
                    notes="Digital text found but could not identify structured student rows. Routing to vision/OCR provider.",
                )

            # Calculate counts
            present = sum(1 for r in candidate_rows if r.attendance_status == AttendanceMarkStatus.PRESENT)
            absent = sum(1 for r in candidate_rows if r.attendance_status == AttendanceMarkStatus.ABSENT)
            unknown = sum(1 for r in candidate_rows if r.attendance_status == AttendanceMarkStatus.UNKNOWN)

            return ExtractionDocumentResult(
                provider=self.name,
                status="success",
                page_count=page_count,
                rows=candidate_rows,
                total_candidate_rows=len(candidate_rows),
                valid_rows=len(candidate_rows),
                present_count=present,
                absent_count=absent,
                unknown_count=unknown,
                notes=f"Successfully extracted {len(candidate_rows)} student rows across {page_count} page(s) directly from digital PDF.",
            )

        except Exception as e:
            logger.exception("PyMuPDF direct extraction error: %s", e)
            return ExtractionDocumentResult(
                provider=self.name,
                status="failed",
                errors=[f"PyMuPDF error: {str(e)}"],
            )

    def _parse_table_row(
        self, cells: List[str], page_num: int, default_index: int
    ) -> Optional[CandidateRow]:
        """Examine a row of table cells and return a CandidateRow if a USN is found."""
        usn_val: Optional[str] = None
        name_val: Optional[str] = None
        mark_val: Optional[str] = None
        usn_col_idx = -1

        for idx, cell in enumerate(cells):
            m = USN_REGEX.search(cell)
            if m:
                token = m.group(0).upper()
                # Must contain both letter and digit to be a real USN
                if any(c.isdigit() for c in token) and any(c.isalpha() for c in token):
                    usn_val = token
                    usn_col_idx = idx
                    break

        if not usn_val:
            return None

        # Look for name: cell near USN containing alphabetic words (length > 2, not a header)
        for idx, cell in enumerate(cells):
            if idx == usn_col_idx:
                continue
            if cell.isdigit() or len(cell) < 2:
                continue
            if any(h in cell.lower() for h in ["roll", "usn", "programme", "faculty", "signature", "page"]):
                continue
            # If cell has mostly letters and spaces
            letters_only = re.sub(r"[^A-Za-z\s.]", "", cell).strip()
            if len(letters_only) >= 3 and not re.search(r"\d", cell):
                name_val = letters_only
                break

        # Look for attendance mark in remaining cells (P, A, Present, Absent)
        for idx, cell in enumerate(cells):
            if idx in (usn_col_idx,):
                continue
            upper = cell.upper().strip()
            if upper in ("P", "PRESENT", "YES", "1"):
                mark_val = "P"
                break
            elif upper in ("A", "ABSENT", "NO", "0"):
                mark_val = "A"
                break
            elif upper in ("✓", "✔", "+"):
                mark_val = "P"
                break
            elif upper in ("✗", "X", "-"):
                mark_val = "A"
                break

        status = AttendanceMarkStatus.UNKNOWN
        if mark_val == "P":
            status = AttendanceMarkStatus.PRESENT
        elif mark_val == "A":
            status = AttendanceMarkStatus.ABSENT

        return CandidateRow(
            page_number=page_num,
            row_index=default_index,
            student_name=name_val,
            usn=usn_val,
            raw_attendance_mark=mark_val,
            attendance_status=status,
            match_status=MatchStatus.UNMATCHED,
            confidence=1.0,
            review_required=(status == AttendanceMarkStatus.UNKNOWN),
            review_reason="Attendance mark unclear" if status == AttendanceMarkStatus.UNKNOWN else None,
        )

    def _parse_text_line(
        self, line: str, page_num: int, default_index: int
    ) -> Optional[CandidateRow]:
        """Extract USN and potential student name from a text line."""
        m = USN_REGEX.search(line)
        if not m:
            return None
        token = m.group(0).upper()
        if not (any(c.isdigit() for c in token) and any(c.isalpha() for c in token)):
            return None

        # Try to find attendance mark at end or bounded by spaces
        mark_val = None
        status = AttendanceMarkStatus.UNKNOWN
        if re.search(r"\b[PA]\b", line):
            marks = re.findall(r"\b([PA])\b", line)
            mark_val = marks[-1]
            status = AttendanceMarkStatus.PRESENT if mark_val == "P" else AttendanceMarkStatus.ABSENT

        # Clean line to extract candidate name
        line_no_usn = line.replace(token, "")
        name_cand = re.sub(r"[^A-Za-z\s.]", " ", line_no_usn).strip()
        name_cand = re.sub(r"\s+", " ", name_cand)
        name_val = name_cand if len(name_cand) > 3 else None

        return CandidateRow(
            page_number=page_num,
            row_index=default_index,
            student_name=name_val,
            usn=token,
            raw_attendance_mark=mark_val,
            attendance_status=status,
            match_status=MatchStatus.UNMATCHED,
            confidence=0.9,
            review_required=(status == AttendanceMarkStatus.UNKNOWN),
            review_reason="Attendance mark unclear" if status == AttendanceMarkStatus.UNKNOWN else None,
        )

    @staticmethod
    def render_pdf_to_images(file_path: str, dpi: int = 300) -> List[bytes]:
        """
        Convert all pages of a PDF to high-resolution PNG bytes.
        Fast C-based rendering via PyMuPDF without requiring poppler binaries.
        """
        doc = pymupdf.open(file_path)
        images = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            images.append(pix.tobytes("png"))
        return images
