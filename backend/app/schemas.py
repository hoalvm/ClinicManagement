from datetime import datetime, time

from pydantic import BaseModel, ConfigDict, Field


# ---------- User ----------
class UserBase(BaseModel):
    Username: str
    FullName: str
    Phone: str | None = None
    Email: str | None = None
    Role: str = Field(..., pattern="^(PATIENT|DOCTOR|STAFF|ADMIN)$", description="PATIENT, DOCTOR, STAFF, ADMIN")

class UserCreate(UserBase):
    Password: str

class UserUpdate(BaseModel):
    Username: str | None = None
    FullName: str | None = None
    Phone: str | None = None
    Email: str | None = None
    Role: str | None = Field(None, pattern="^(PATIENT|DOCTOR|STAFF|ADMIN)$")
    IsActive: bool | None = None

class UserOut(UserBase):
    UserID: int
    IsActive: bool
    CreatedAt: datetime
    model_config = ConfigDict(from_attributes=True)

class LoginRequest(BaseModel):
    Username: str
    Password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- Specialty ----------
class SpecialtyCreate(BaseModel):
    SpecialtyName: str
    Description: str | None = None

class SpecialtyUpdate(BaseModel):
    SpecialtyName: str | None = None
    Description: str | None = None
    IsActive: bool | None = None

class SpecialtyOut(BaseModel):
    SpecialtyID: int
    SpecialtyName: str
    Description: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)

# ---------- Clinic ----------
class ClinicCreate(BaseModel):
    ClinicName: str
    Address: str | None = None
    Phone: str | None = None

class ClinicUpdate(BaseModel):
    ClinicName: str | None = None
    Address: str | None = None
    Phone: str | None = None
    IsActive: bool | None = None

class ClinicOut(BaseModel):
    ClinicID: int
    ClinicName: str
    Address: str | None = None
    Phone: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)

# ---------- Doctor ----------
class DoctorCreate(BaseModel):
    Username: str
    Password: str
    FullName: str
    Phone: str | None = None
    Email: str | None = None
    SpecialtyID: int
    ClinicID: int | None = None
    LicenseNumber: str | None = None

class DoctorUpdate(BaseModel):
    SpecialtyID: int | None = None
    ClinicID: int | None = None
    LicenseNumber: str | None = None
    IsActive: bool | None = None

class DoctorOut(BaseModel):
    DoctorID: int
    UserID: int
    FullName: str
    SpecialtyID: int
    SpecialtyName: str | None = None
    ClinicID: int | None = None
    ClinicName: str | None = None
    LicenseNumber: str | None = None
    IsActive: bool
    model_config = ConfigDict(from_attributes=True)

# ---------- DoctorSchedule ----------
class ScheduleCreate(BaseModel):
    DoctorID: int
    DayOfWeek: int = Field(..., ge=1, le=7, description="Thứ 2 (1) đến Chủ Nhật (7)")
    StartTime: time
    EndTime: time
    SlotDuration: int = Field(30, gt=0, description="Thời lượng ca khám (phút) > 0")

class ScheduleUpdate(BaseModel):
    DayOfWeek: int | None = Field(None, ge=1, le=7)
    StartTime: time | None = None
    EndTime: time | None = None
    SlotDuration: int | None = Field(None, gt=0)
    IsActive: bool | None = None

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