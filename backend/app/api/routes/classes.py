from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.models.class_ import Class
from app.models.user import User
from app.schemas.class_ import ClassCreate, ClassUpdate, ClassOut
from app.services.audit_service import log_event

router = APIRouter(prefix="/classes", tags=["Classes"])


@router.get("", response_model=List[ClassOut])
async def list_classes(
    department_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Class)
    if department_id:
        q = q.where(Class.department_id == department_id)
    result = await db.execute(q.order_by(Class.name))
    return result.scalars().all()


@router.post("", response_model=ClassOut, status_code=201)
async def create_class(
    body: ClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cls = Class(**body.model_dump())
    db.add(cls)
    await db.flush()
    await log_event(db, "class_created", current_user.id, "class", cls.id)
    await db.commit()
    await db.refresh(cls)
    return cls


@router.get("/{class_id}", response_model=ClassOut)
async def get_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    return cls


@router.patch("/{class_id}", response_model=ClassOut)
async def update_class(
    class_id: int,
    body: ClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(cls, k, v)
    await db.flush()
    await log_event(db, "class_updated", current_user.id, "class", class_id)
    await db.commit()
    await db.refresh(cls)
    return cls


@router.delete("/{class_id}", status_code=204)
async def delete_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    cls = await db.get(Class, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.delete(cls)
    await log_event(db, "class_deleted", current_user.id, "class", class_id)
    await db.commit()
