from pydantic import BaseModel
from typing import Optional


# Slim nested schemas — no deep nesting to avoid lazy-load issues
class _LecturerSlim(BaseModel):
    id: int
    employee_id: str
    full_name: str
    department_id: int
    is_active: bool
    user_id: int
    model_config = {"from_attributes": True}


class _SubjectSlim(BaseModel):
    id: int
    subject_code: str
    subject_name: str
    semester: int
    department_id: int
    model_config = {"from_attributes": True}


class _ClassSlim(BaseModel):
    id: int
    name: str
    academic_year: str
    semester: int
    department_id: int
    model_config = {"from_attributes": True}


class AssignmentCreate(BaseModel):
    lecturer_id: int
    subject_id: int
    class_id: int


class AssignmentOut(BaseModel):
    id: int
    lecturer_id: int
    subject_id: int
    class_id: int
    lecturer: Optional[_LecturerSlim] = None
    subject: Optional[_SubjectSlim] = None
    class_: Optional[_ClassSlim] = None

    model_config = {"from_attributes": True}
