from pydantic import BaseModel
from typing import Optional


class ClassBase(BaseModel):
    name: str
    academic_year: str
    semester: int
    department_id: int


class ClassCreate(ClassBase):
    pass


class ClassUpdate(BaseModel):
    name: Optional[str] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    department_id: Optional[int] = None


class ClassOut(ClassBase):
    id: int
    # department omitted — use department_id directly to avoid lazy-load
    # (the admin UI looks up department names from its own departments query)

    model_config = {"from_attributes": True}
