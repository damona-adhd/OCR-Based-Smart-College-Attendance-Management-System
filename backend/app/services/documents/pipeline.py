"""Modular document processing: inspect → extract → validate → match USNs."""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.source_file import SourceFile, ProcessingStatus
from app.models.student import Student
from app.schemas.ocr import OCRProcessingResult, OCRRowResult, MatchStatus
from app.services.documents.inspector import inspect_file
from app.services.documents.extractors import (
    extract_rows_from_text,
    extract_roster_from_text,
    extract_with_gemini,
)
from app.services.ocr.matcher import match_students, find_missing_students, normalize_usn
from app.services.settings_service import get_setting

logger = logging.getLogger(__name__)


def file_checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


async def _class_roster(db: AsyncSession, class_id: int) -> List[Dict[str, Any]]:
    result = await db.execute(
        select(Student).where(Student.class_id == class_id, Student.is_active == True)  # noqa: E712
    )
    return [{"id": s.id, "usn": s.usn, "full_name": s.full_name} for s in result.scalars().all()]


def _match_to_ocr_rows(extracted: List[Dict[str, Any]], roster: List[Dict[str, Any]]) -> List[OCRRowResult]:
    extracted_usns = [
        {"usn": r["usn"], "name": r.get("name"), "confidence": r.get("confidence", 70), "raw_text": r.get("raw_line")}
        for r in extracted
    ]
    matched = match_students(extracted_usns, roster)
    by_usn = {normalize_usn(r["usn"]): r for r in extracted}
    rows: List[OCRRowResult] = []
    for i, m in enumerate(matched):
        src = by_usn.get(normalize_usn(m.get("extracted_usn") or ""), {})
        mark = src.get("mark")
        uncertain = bool(src.get("uncertain")) or m["match_status"] != MatchStatus.MATCHED
        proposed = mark if mark in ("present", "absent") and m["match_status"] == MatchStatus.MATCHED else None
        if proposed is None:
            uncertain = True
        rows.append(
            OCRRowResult(
                row_index=i,
                extracted_usn=m.get("extracted_usn"),
                extracted_name=m.get("extracted_name") or src.get("name"),
                confidence=float(m.get("confidence") or src.get("confidence") or 0),
                match_status=m["match_status"],
                matched_student_id=m.get("matched_student_id"),
                matched_student_name=m.get("matched_student_name"),
                matched_student_usn=m.get("matched_student_usn"),
                proposed_status=proposed,
                needs_review=uncertain or m["match_status"] != MatchStatus.MATCHED,
            )
        )
    missing = find_missing_students(matched, roster)
    offset = len(rows)
    for j, miss in enumerate(missing):
        rows.append(
            OCRRowResult(
                row_index=offset + j,
                extracted_usn=None,
                extracted_name=None,
                confidence=0,
                match_status=MatchStatus.MISSING,
                matched_student_id=miss["id"],
                matched_student_name=miss["full_name"],
                matched_student_usn=miss["usn"],
                proposed_status=None,
                needs_review=True,
            )
        )
    return rows


async def process_register_document(
    db: AsyncSession,
    source_file_id: int,
    session_id: int,
    class_id: int,
) -> OCRProcessingResult:
    sf = await db.get(SourceFile, source_file_id)
    if not sf:
        raise ValueError(f"Source file {source_file_id} not found")

    sf.processing_status = ProcessingStatus.PROCESSING
    await db.flush()

    file_path = os.path.join(settings.UPLOAD_DIR, sf.storage_key)
    if not os.path.exists(file_path):
        sf.processing_status = ProcessingStatus.FAILED
        await db.flush()
        raise FileNotFoundError("Uploaded file not found on disk")

    checksum = file_checksum(file_path)
    sf.checksum = checksum
    sf.purpose = sf.purpose or "register"

    roster = await _class_roster(db, class_id)
    if not roster:
        sf.processing_status = ProcessingStatus.COMPLETED
        await db.flush()
        return OCRProcessingResult(
            source_file_id=source_file_id,
            session_id=session_id,
            rows=[],
            total_extracted=0,
            total_matched=0,
            total_unmatched=0,
            total_uncertain=0,
            processing_note="No students are enrolled in this class. Add students before extracting attendance.",
        )

    provider = (await get_setting(db, "extraction_provider", settings.EXTRACTION_PROVIDER)).strip().lower()
    inspection = inspect_file(file_path, sf.mime_type)
    extracted: List[Dict[str, Any]] = []
    notes = [inspection.note]

    try:
        if inspection.kind == "pdf_text":
            extracted = extract_rows_from_text(inspection.sample_text)
            notes.append("Used direct PDF text extraction (no OCR).")
        elif provider == "gemini" and settings.GEMINI_API_KEY:
            with open(file_path, "rb") as f:
                data = f.read()
            extracted = await extract_with_gemini(data, sf.mime_type or "image/jpeg")
            notes.append("Used the configured vision model for a scanned register.")
        else:
            sf.processing_status = ProcessingStatus.COMPLETED
            await db.flush()
            reason = (
                "Document extraction is unavailable because the extraction provider is not configured. "
                "You can still mark attendance manually."
                if inspection.kind != "pdf_text"
                else "No student identifiers could be read from this document."
            )
            if inspection.kind != "pdf_text":
                return OCRProcessingResult(
                    source_file_id=source_file_id,
                    session_id=session_id,
                    rows=[],
                    total_extracted=0,
                    total_matched=0,
                    total_unmatched=0,
                    total_uncertain=0,
                    processing_note=reason,
                )
        rows = _match_to_ocr_rows(extracted, roster)
        sf.processing_status = ProcessingStatus.COMPLETED
        await db.flush()
        return OCRProcessingResult(
            source_file_id=source_file_id,
            session_id=session_id,
            rows=rows,
            total_extracted=len(extracted),
            total_matched=sum(1 for r in rows if r.match_status == MatchStatus.MATCHED),
            total_unmatched=sum(1 for r in rows if r.match_status == MatchStatus.UNMATCHED),
            total_uncertain=sum(1 for r in rows if r.needs_review),
            processing_note=" ".join(notes),
        )
    except Exception as exc:
        logger.exception("document processing failed")
        sf.processing_status = ProcessingStatus.FAILED
        await db.flush()
        raise RuntimeError(str(exc)) from exc


async def preview_roster_pdf(file_path: str, mime_type: str) -> Dict[str, Any]:
    inspection = inspect_file(file_path, mime_type)
    if inspection.kind != "pdf_text":
        return {
            "kind": inspection.kind,
            "page_count": inspection.page_count,
            "rows": [],
            "note": (
                "This PDF does not contain selectable text. "
                "Use a digitally generated roster, or add students manually."
            ),
        }
    rows = extract_roster_from_text(inspection.sample_text)
    return {
        "kind": inspection.kind,
        "page_count": inspection.page_count,
        "rows": rows,
        "note": "Extracted from the PDF text layer. Review every row before importing.",
    }
