import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User, UserRole
from app.models.source_file import SourceFile, ProcessingStatus
from app.models.attendance_session import AttendanceSession

router = APIRouter(prefix="/files", tags=["File Upload"])

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/jpg", "application/pdf"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


def _validate_upload(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed. Use JPG or PNG.",
        )
    ext = os.path.splitext(file.filename or "")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File extension {ext} not allowed")


@router.post("/upload/{session_id}", response_model=dict)
async def upload_register_image(
    session_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an attendance register image for OCR processing."""
    if current_user.role not in (UserRole.LECTURER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Not authorized")

    session = await db.get(AttendanceSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    _validate_upload(file)

    # Read content and validate size
    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    # Save to protected upload directory
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or ".jpg")[-1].lower()
    storage_key = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, storage_key)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create source file record
    sf = SourceFile(
        attendance_session_id=session_id,
        original_filename=file.filename or "upload",
        storage_key=storage_key,
        mime_type=file.content_type,
        file_size=len(content),
        processing_status=ProcessingStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    db.add(sf)
    await db.flush()

    # Link to session
    session.source_file_id = sf.id
    await db.flush()

    await db.commit()
    await db.refresh(sf)

    return {
        "source_file_id": sf.id,
        "session_id": session_id,
        "original_filename": sf.original_filename,
        "file_size": sf.file_size,
        "processing_status": sf.processing_status,
    }


@router.get("/image/{session_id}")
async def get_session_image(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Serve the uploaded image for an authorized user."""
    from sqlalchemy import select
    from app.models.lecturer import Lecturer

    session = await db.get(AttendanceSession, session_id)
    if not session or not session.source_file_id:
        raise HTTPException(status_code=404, detail="No image found for this session")

    # Authorization: lecturer must own session; admin always allowed
    if current_user.role == UserRole.LECTURER:
        lec_result = await db.execute(
            select(Lecturer).where(Lecturer.user_id == current_user.id)
        )
        lecturer = lec_result.scalar_one_or_none()
        if not lecturer or session.lecturer_id != lecturer.id:
            raise HTTPException(status_code=403, detail="Access denied")

    sf = await db.get(SourceFile, session.source_file_id)
    if not sf:
        raise HTTPException(status_code=404, detail="File record not found")

    file_path = os.path.join(settings.UPLOAD_DIR, sf.storage_key)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(file_path, media_type=sf.mime_type)
