"""Medical history and result schemas."""

from datetime import datetime

from backend.app.schemas.appointment import ClinicSummary, DoctorSummary
from backend.app.schemas.common import APIModel, Page


class MedicalRecordSummary(APIModel):
    medical_record_id: int
    appointment_id: int
    examination_date: datetime
    diagnosis: str | None = None
    doctor: DoctorSummary


class MedicalRecordPage(Page[MedicalRecordSummary]):
    """Paginated medical history response."""


class PrescriptionItemResponse(APIModel):
    medicine_name: str
    quantity: int
    dosage: str | None = None
    instructions: str | None = None


class PrescriptionResponse(APIModel):
    prescription_id: int
    created_at: datetime
    items: list[PrescriptionItemResponse]


class MedicalRecordDetail(APIModel):
    medical_record_id: int
    appointment_id: int
    examination_date: datetime
    symptoms: str | None = None
    diagnosis: str | None = None
    notes: str | None = None
    doctor: DoctorSummary
    clinic: ClinicSummary | None = None
    prescription: PrescriptionResponse | None = None
