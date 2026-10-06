"""Import all mappings so SQLAlchemy can resolve relationship names."""

from backend.app.models.appointment import Appointment
from backend.app.models.base import Base
from backend.app.models.charge_catalog import ChargeCatalog
from backend.app.models.clinic import Clinic
from backend.app.models.doctor import Doctor
from backend.app.models.doctor_schedule import DoctorSchedule
from backend.app.models.doctor_schedule_exception import DoctorScheduleException
from backend.app.models.invoice import Invoice
from backend.app.models.invoice_item import InvoiceItem
from backend.app.models.medical_record import MedicalRecord
from backend.app.models.patient import Patient
from backend.app.models.payment import Payment
from backend.app.models.prescription import Prescription
from backend.app.models.prescription_item import PrescriptionItem
from backend.app.models.specialty import Specialty
from backend.app.models.staff_clinic_assignment import StaffClinicAssignment
from backend.app.models.user import User

__all__ = [
    "Appointment",
    "Base",
    "ChargeCatalog",
    "Clinic",
    "Doctor",
    "DoctorSchedule",
    "DoctorScheduleException",
    "Invoice",
    "InvoiceItem",
    "MedicalRecord",
    "Patient",
    "Payment",
    "Prescription",
    "PrescriptionItem",
    "Specialty",
    "StaffClinicAssignment",
    "User",
]
