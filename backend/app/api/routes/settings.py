from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.app_setting import AppSetting
from app.models.user import User

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingOut(dict):
    pass


@router.get("", response_model=List[dict])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(AppSetting))
    return [{"key": s.key, "value": s.value, "description": s.description} for s in result.scalars().all()]


@router.put("/{key}")
async def update_setting(
    key: str,
    value: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
    await db.commit()
    return {"key": key, "value": value}
