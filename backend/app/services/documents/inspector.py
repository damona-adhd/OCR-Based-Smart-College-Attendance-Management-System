"""Inspect uploaded files: digital PDF vs scanned images."""
from dataclasses import dataclass
from typing import Optional

import fitz  # PyMuPDF


@dataclass
class InspectionResult:
    kind: str  # pdf_text | pdf_scan | image
    page_count: int
    has_text_layer: bool
    sample_text: str = ""
    note: str = ""


def inspect_file(path: str, mime_type: Optional[str] = None) -> InspectionResult:
    is_pdf = (mime_type == "application/pdf") or path.lower().endswith(".pdf")
    if not is_pdf:
        return InspectionResult(kind="image", page_count=1, has_text_layer=False)

    doc = fitz.open(path)
    try:
        page_count = doc.page_count
        text_chars = 0
        sample_parts = []
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            text_chars += len(text.strip())
            if i < 3:
                sample_parts.append(text)
        has_text = text_chars >= 40
        return InspectionResult(
            kind="pdf_text" if has_text else "pdf_scan",
            page_count=page_count,
            has_text_layer=has_text,
            sample_text="\n".join(sample_parts),
            note="Digital PDF with a text layer" if has_text else "PDF appears scanned (little or no selectable text)",
        )
    finally:
        doc.close()
