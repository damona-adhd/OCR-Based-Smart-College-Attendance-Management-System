from pydantic import BaseModel
from typing import Optional


class SubjectBase(BaseModel):
    subject_code: str
    subject_name: str
    semester: int
    department_id: int


class SubjectCreate(SubjectBase):
    pass


class SubjectQuickCreate(BaseModel):
    subject_name: str
    subject_code: str
    department_id: Optional[int] = None
    semester: Optional[int] = None
    class_id: Optional[int] = None


class SubjectUpdate(BaseModel):
    subject_code: Optional[str] = None
    subject_name: Optional[str] = None
    semester: Optional[int] = None
    department_id: Optional[int] = None


class SubjectOut(SubjectBase):
    id: int
    # department omitted — use department_id directly to avoid lazy-load

    model_config = {"from_attributes": True}
