from datetime import date, time

from pydantic import BaseModel, Field


class DoctorLoginRequest(BaseModel):
    username: str
    password: str

class DoctorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: int
    doctor_name: str
    license_number: str | None

class PrescriptionItemCreate(BaseModel):
    medicine_name: str
    quantity: int = Field(gt=0)
    dosage: str | None = None
    instructions: str | None = None

class CompleteExamRequest(BaseModel):
    symptoms: str
    diagnosis: str
    notes: str | None = None
    prescription_items: list[PrescriptionItemCreate] = []

class PatientResponse(BaseModel):
    PatientID: int
    FullName: str
    Phone: str | None
    DateOfBirth: date | None
    Gender: str | None
    Address: str | None

class AppointmentResponse(BaseModel):
    AppointmentID: int
    AppointmentDate: date
    StartTime: time
    EndTime: time
    Reason: str | None
    Status: str
    Patient: PatientResponse