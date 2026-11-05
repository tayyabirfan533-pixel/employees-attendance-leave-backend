from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator

class EmployeeCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str
    password: str = Field(min_length=8)
    department: str | None = None

class EmployeeUpdate(BaseModel):
    full_name: str | None = None
    department: str | None = None
    is_active: bool | None = None

class EmployeeOut(BaseModel):
    id: int
    full_name: str
    email: str
    department: str | None
    role: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=2000)
    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self

class LeaveReview(BaseModel):
    status: str
    admin_comment: str | None = None
    @model_validator(mode="after")
    def validate_status(self):
        if self.status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        return self

class LeaveOut(BaseModel):
    id: int
    employee_id: int
    start_date: date
    end_date: date
    reason: str
    status: str
    admin_comment: str | None
    created_at: datetime
    reviewed_at: datetime | None
    model_config = ConfigDict(from_attributes=True)
