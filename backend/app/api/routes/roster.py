"""Roster PDF import router for administrators."""
import os
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.core.config import settings
from app.models.user import User
from app.models.student import Student
from app.models.class_ import Class
from app.models.department import Department
from app.services.documents.inspector import inspect_file
from app.services.documents.extractors import extract_roster_from_text
from app.services.audit_service import log_event

router = APIRouter(prefix="/roster", tags=["Roster"])


class RosterPreviewRow(BaseModel):
    usn: str
    full_name: str
    status: str  # "new", "existing", "invalid"
    notes: Optional[str] = None


class RosterPreviewResponse(BaseModel):
    filename: str
    page_count: int
    kind: str
    has_text_layer: bool
    total_extracted: int
    new_count: int
    existing_count: int
    invalid_count: int
    rows: List[RosterPreviewRow]
    note: str


class RosterImportItem(BaseModel):
    usn: str
    full_name: str


class RosterImportRequest(BaseModel):
    class_id: int
    students: List[RosterImportItem]


class RosterImportResponse(BaseModel):
    imported_count: int
    skipped_count: int
    class_id: int
    message: str


@router.post("/preview", response_model=RosterPreviewResponse)
async def preview_roster_upload(
    file: UploadFile = File(...),
    class_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Inspect and extract students from a roster PDF without saving."""
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF document",
        )

    content = await file.read()
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_key = f"roster_preview_{uuid.uuid4().hex}.pdf"
    temp_path = os.path.join(settings.UPLOAD_DIR, temp_key)

    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        inspection = inspect_file(temp_path, mime_type="application/pdf")
        if not inspection.has_text_layer:
            return RosterPreviewResponse(
                filename=file.filename or "roster.pdf",
                page_count=inspection.page_count,
                kind=inspection.kind,
                has_text_layer=False,
                total_extracted=0,
                new_count=0,
                existing_count=0,
                invalid_count=0,
                rows=[],
                note="This PDF does not appear to contain selectable text (may be scanned). Please upload a digital PDF roster or add students manually.",
            )

        extracted_raw = extract_roster_from_text(inspection.sample_text)

        # Retrieve existing USNs from DB
        existing_usn_res = await db.execute(select(Student.usn))
        existing_usns = {u.strip().upper() for u in existing_usn_res.scalars().all()}

        preview_rows: List[RosterPreviewRow] = []
        seen_in_batch = set()
        new_c = 0
        existing_c = 0
        invalid_c = 0

        for r in extracted_raw:
            usn_val = r["usn"].strip().upper()
            name_val = r["full_name"].strip() or "Unknown Student"

            if not usn_val or len(usn_val) < 4:
                preview_rows.append(
                    RosterPreviewRow(
                        usn=usn_val or "UNKNOWN",
                        full_name=name_val,
                        status="invalid",
                        notes="USN format invalid or incomplete",
                    )
                )
                invalid_c += 1
            elif usn_val in seen_in_batch:
                preview_rows.append(
                    RosterPreviewRow(
                        usn=usn_val,
                        full_name=name_val,
                        status="invalid",
                        notes="Duplicate USN within uploaded PDF",
                    )
                )
                invalid_c += 1
            elif usn_val in existing_usns:
                preview_rows.append(
                    RosterPreviewRow(
                        usn=usn_val,
                        full_name=name_val,
                        status="existing",
                        notes="Already exists in database",
                    )
                )
                existing_c += 1
                seen_in_batch.add(usn_val)
            else:
                preview_rows.append(
                    RosterPreviewRow(
                        usn=usn_val,
                        full_name=name_val,
                        status="new",
                        notes="Ready to import",
                    )
                )
                new_c += 1
                seen_in_batch.add(usn_val)

        return RosterPreviewResponse(
            filename=file.filename or "roster.pdf",
            page_count=inspection.page_count,
            kind=inspection.kind,
            has_text_layer=True,
            total_extracted=len(preview_rows),
            new_count=new_c,
            existing_count=existing_c,
            invalid_count=invalid_c,
            rows=preview_rows,
            note="Direct text extraction completed. Review extracted rows before confirming import.",
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@router.post("/import", response_model=RosterImportResponse)
async def commit_roster_import(
    body: RosterImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Commit verified students from preview to database atomically."""
    target_class = await db.get(Class, body.class_id)
    if not target_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target class ID {body.class_id} not found",
        )

    # Check existing USNs in DB to guarantee idempotency and avoid duplicates
    existing_usn_res = await db.execute(select(Student.usn))
    existing_usns = {u.strip().upper() for u in existing_usn_res.scalars().all()}

    imported = 0
    skipped = 0
    created_students = []

    for item in body.students:
        clean_usn = item.usn.strip().upper()
        clean_name = item.full_name.strip()

        if not clean_usn or clean_usn in existing_usns or not clean_name:
            skipped += 1
            continue

        student = Student(
            usn=clean_usn,
            full_name=clean_name,
            department_id=target_class.department_id,
            academic_year=target_class.academic_year,
            semester=target_class.semester,
            course=target_class.course,
            class_id=target_class.id,
            is_active=True,
        )
        db.add(student)
        existing_usns.add(clean_usn)
        created_students.append(clean_usn)
        imported += 1

    await db.flush()
    await log_event(
        db,
        action="roster_imported",
        actor_user_id=current_user.id,
        entity_type="class",
        entity_id=target_class.id,
        details={
            "imported_count": imported,
            "skipped_count": skipped,
            "sample_usns": created_students[:5],
        },
    )
    await db.commit()

    return RosterImportResponse(
        imported_count=imported,
        skipped_count=skipped,
        class_id=target_class.id,
        message=f"Successfully imported {imported} students into {target_class.name} ({skipped} skipped/duplicate).",
    )
