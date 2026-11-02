"""
Main OCR and document extraction service adapter.
Delegates to the ExtractionOrchestrator for multi-provider processing
(Gemini Vision, PyMuPDF Direct Extraction, OpenCV Grid Detection, Tesseract Fallback).
"""
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.source_file import SourceFile, ProcessingStatus
from app.schemas.ocr import OCRProcessingResult
from app.core.config import settings
from app.services.extraction.orchestrator import extraction_orchestrator

logger = logging.getLogger(__name__)


async def process_register_image(
    db: AsyncSession,
    source_file_id: int,
    session_id: int,
    class_id: int,
    forced_provider: str = None,
) -> OCRProcessingResult:
    """
    Execute document extraction pipeline for an uploaded attendance register (image or PDF).
    Uses configured provider strategy (auto, gemini, pymupdf, tesseract).
    Preserves all extracted candidate rows and matches against the database class roster.
    """
    sf = await db.get(SourceFile, source_file_id)
    if not sf:
        raise ValueError(f"Source file {source_file_id} not found")

    sf.processing_status = ProcessingStatus.PROCESSING
    await db.flush()

    try:
        file_path = os.path.join(settings.UPLOAD_DIR, sf.storage_key)
        logger.info("process_register_image: file=%s mime=%s session=%d class=%d", file_path, sf.mime_type, session_id, class_id)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Uploaded file not found on disk: {file_path}")

        result = await extraction_orchestrator.process_document(
            db=db,
            file_path=file_path,
            mime_type=sf.mime_type,
            session_id=session_id,
            source_file_id=source_file_id,
            class_id=class_id,
            forced_provider=forced_provider,
        )

        sf.processing_status = ProcessingStatus.COMPLETED
        await db.flush()
        return result

    except Exception as e:
        logger.exception("process_register_image failed: %s", e)
        sf.processing_status = ProcessingStatus.FAILED
        await db.flush()
        raise
