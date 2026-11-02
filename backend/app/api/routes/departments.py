from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentOut
from app.services.audit_service import log_event

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("", response_model=List[DepartmentOut])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Department).order_by(Department.name))
    return result.scalars().all()


@router.post("", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    existing = await db.execute(select(Department).where(Department.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Department code already exists")
    dept = Department(name=body.name, code=body.code)
    db.add(dept)
    await db.flush()
    await log_event(db, "department_created", current_user.id, "department", dept.id)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.get("/{dept_id}", response_model=DepartmentOut)
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    body: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    if body.name is not None:
        dept.name = body.name
    if body.code is not None:
        dept.code = body.code.upper()
    await db.flush()
    await log_event(db, "department_updated", current_user.id, "department", dept_id)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(dept)
    await log_event(db, "department_deleted", current_user.id, "department", dept_id)
    await db.commit()
