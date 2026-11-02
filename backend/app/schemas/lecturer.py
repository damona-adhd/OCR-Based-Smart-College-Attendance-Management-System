from pydantic import BaseModel, EmailStr
from typing import Optional


class LecturerCreate(BaseModel):
    employee_id: str
    full_name: str
    department_id: int
    username: str
    email: EmailStr
    password: str


class LecturerUpdate(BaseModel):
    employee_id: Optional[str] = None
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    is_active: Optional[bool] = None


class LecturerOut(BaseModel):
    id: int
    employee_id: str
    full_name: str
    department_id: int
    is_active: bool
    user_id: int

    model_config = {"from_attributes": True}


class LecturerWithUser(LecturerOut):
    username: Optional[str] = None
    email: Optional[str] = None
