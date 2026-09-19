"""Patient dashboard schema."""

from backend.app.schemas.appointment import AppointmentSummary
from backend.app.schemas.common import APIModel


class DashboardResponse(APIModel):
    patient_name: str
    total_appointments: int
    total_medical_records: int
    total_invoices: int
    unpaid_invoices: int
    upcoming_appointment: AppointmentSummary | None = None
