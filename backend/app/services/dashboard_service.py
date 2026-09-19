"""Patient dashboard aggregation business logic."""

from sqlalchemy.orm import Session

from backend.app.models import Patient
from backend.app.repositories import (
    AppointmentRepository,
    InvoiceRepository,
    MedicalRecordRepository,
)
from backend.app.schemas.dashboard import DashboardResponse
from backend.app.services.appointment_service import AppointmentService


class DashboardService:
    def __init__(self, session: Session) -> None:
        self.appointments = AppointmentRepository(session)
        self.medical_records = MedicalRecordRepository(session)
        self.invoices = InvoiceRepository(session)
        self.appointment_service = AppointmentService(session)

    def get_dashboard(self, patient: Patient) -> DashboardResponse:
        patient_id = patient.patient_id
        return DashboardResponse(
            patient_name=patient.user.full_name,
            total_appointments=self.appointments.count_for_patient(patient_id),
            total_medical_records=self.medical_records.count_for_patient(patient_id),
            total_invoices=self.invoices.count_for_patient(patient_id),
            unpaid_invoices=self.invoices.count_for_patient(patient_id, status="UNPAID"),
            upcoming_appointment=self.appointment_service.get_upcoming(patient_id),
        )
