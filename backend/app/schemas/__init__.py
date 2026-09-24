"""Pydantic request and response schemas.

Re-exports legacy flat schemas so that `from . import schemas; schemas.UserOut`
still works alongside the new sub-module layout.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, time

# ---------- User ----------
class UserBase(BaseModel):
    Username: str
    FullName: str
    Phone: Optional[str] = None
    Email: Optional[str] = None
    Role: str = Field(..., pattern="^(PATIENT|DOCTOR|STAFF|ADMIN)$", description="PATIENT, DOCTOR, STAFF, ADMIN")

class UserCreate(UserBase):
    Password: str

class UserUpdate(BaseModel):
    Username: Optional[str] = None
    FullName: Optional[str] = None
    Phone: Optional[str] = None
    Email: Optional[str] = None
    Role: Optional[str] = Field(None, pattern="^(PATIENT|DOCTOR|STAFF|ADMIN)$")
    IsActive: Optional[bool] = None

class UserOut(UserBase):
    UserID: int
    IsActive: bool
    CreatedAt: datetime
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    Username: str
    Password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- Specialty ----------
class SpecialtyCreate(BaseModel):
    SpecialtyName: str
    Description: Optional[str] = None

class SpecialtyUpdate(BaseModel):
    SpecialtyName: Optional[str] = None
    Description: Optional[str] = None
    IsActive: Optional[bool] = None

class SpecialtyOut(BaseModel):
    SpecialtyID: int
    SpecialtyName: str
    Description: Optional[str] = None
    IsActive: bool
    class Config:
        from_attributes = True

# ---------- Clinic ----------
class ClinicCreate(BaseModel):
    ClinicName: str
    Address: Optional[str] = None
    Phone: Optional[str] = None

class ClinicUpdate(BaseModel):
    ClinicName: Optional[str] = None
    Address: Optional[str] = None
    Phone: Optional[str] = None
    IsActive: Optional[bool] = None

class ClinicOut(BaseModel):
    ClinicID: int
    ClinicName: str
    Address: Optional[str] = None
    Phone: Optional[str] = None
    IsActive: bool
    class Config:
        from_attributes = True

# ---------- Doctor ----------
class DoctorCreate(BaseModel):
    Username: str
    Password: str
    FullName: str
    Phone: Optional[str] = None
    Email: Optional[str] = None
    SpecialtyID: int
    ClinicID: Optional[int] = None
    LicenseNumber: Optional[str] = None

class DoctorUpdate(BaseModel):
    SpecialtyID: Optional[int] = None
    ClinicID: Optional[int] = None
    LicenseNumber: Optional[str] = None
    IsActive: Optional[bool] = None

class DoctorOut(BaseModel):
    DoctorID: int
    UserID: int
    FullName: str
    SpecialtyID: int
    SpecialtyName: Optional[str] = None
    ClinicID: Optional[int] = None
    ClinicName: Optional[str] = None
    LicenseNumber: Optional[str] = None
    IsActive: bool
    class Config:
        from_attributes = True

# ---------- DoctorSchedule ----------
class ScheduleCreate(BaseModel):
    DoctorID: int
    DayOfWeek: int = Field(..., ge=1, le=7, description="Thứ 2 (1) đến Chủ Nhật (7)")
    StartTime: time
    EndTime: time
    SlotDuration: int = Field(30, gt=0, description="Thời lượng ca khám (phút) > 0")

class ScheduleUpdate(BaseModel):
    DayOfWeek: Optional[int] = Field(None, ge=1, le=7)
    StartTime: Optional[time] = None
    EndTime: Optional[time] = None
    SlotDuration: Optional[int] = Field(None, gt=0)
    IsActive: Optional[bool] = None

class ScheduleOut(BaseModel):
    ScheduleID: int
    DoctorID: int
    DayOfWeek: int
    StartTime: time
    EndTime: time
    SlotDuration: int
    IsActive: bool
    class Config:
        from_attributes = True
