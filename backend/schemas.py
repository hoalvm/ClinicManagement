from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, time

class DoctorLoginRequest(BaseModel):
    username: str
    password: str

class DoctorLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    doctor_id: int
    doctor_name: str
    license_number: Optional[str]

class PrescriptionItemCreate(BaseModel):
    medicine_name: str
    quantity: int = Field(gt=0)
    dosage: Optional[str] = None
    instructions: Optional[str] = None

class CompleteExamRequest(BaseModel):
    symptoms: str
    diagnosis: str
    notes: Optional[str] = None
    prescription_items: List[PrescriptionItemCreate] = []

class PatientResponse(BaseModel):
    PatientID: int
    FullName: str
    Phone: Optional[str]
    DateOfBirth: Optional[date]
    Gender: Optional[str]
    Address: Optional[str]

class AppointmentResponse(BaseModel):
    AppointmentID: int
    AppointmentDate: date
    StartTime: time
    EndTime: time
    Reason: Optional[str]
    Status: str
    Patient: PatientResponse