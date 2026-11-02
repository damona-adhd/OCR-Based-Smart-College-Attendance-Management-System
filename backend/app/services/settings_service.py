from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.app_setting import AppSetting
from app.core.config import settings as app_settings

DEFAULTS = {
    "min_attendance_percentage": str(app_settings.MIN_ATTENDANCE_PERCENTAGE),
    "allow_teacher_create_student": "true",
    "allow_teacher_create_subject": "true",
    "allow_student_correction_requests": "false",
    "usn_pattern": "",
    "extraction_provider": app_settings.EXTRACTION_PROVIDER or "none",
}


async def get_setting(db: AsyncSession, key: str, default: Optional[str] = None) -> str:
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        return row.value
    if default is not None:
        return default
    return DEFAULTS.get(key, "")


async def get_bool_setting(db: AsyncSession, key: str, default: bool = False) -> bool:
    raw = (await get_setting(db, key, "true" if default else "false")).strip().lower()
    return raw in ("1", "true", "yes", "on")
