from pydantic import BaseModel, EmailStr
from typing import Optional


class StudentCreate(BaseModel):
    usn: str
    full_name: str
    department_id: int
    academic_year: str
    semester: int
    class_id: int
    # Optional login account creation
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None


class StudentQuickCreate(BaseModel):
    full_name: str
    usn: str
    class_id: int


class StudentUpdate(BaseModel):
    usn: Optional[str] = None
    full_name: Optional[str] = None
    department_id: Optional[int] = None
    academic_year: Optional[str] = None
    semester: Optional[int] = None
    class_id: Optional[int] = None
    is_active: Optional[bool] = None


class StudentOut(BaseModel):
    id: int
    usn: str
    full_name: str
    department_id: int
    academic_year: str
    semester: int
    class_id: int
    is_active: bool
    user_id: Optional[int] = None

    model_config = {"from_attributes": True}


class StudentWithUser(StudentOut):
    username: Optional[str] = None
    email: Optional[str] = None
