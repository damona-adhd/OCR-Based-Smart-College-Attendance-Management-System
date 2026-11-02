from pydantic import BaseModel, field_validator


class DepartmentBase(BaseModel):
    name: str
    code: str

    @field_validator("code")
    @classmethod
    def uppercase_code(cls, v: str) -> str:
        return v.strip().upper()


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


class DepartmentOut(DepartmentBase):
    id: int

    model_config = {"from_attributes": True}
