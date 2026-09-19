"""Medical history and result business logic."""

from sqlalchemy.orm import Session

from backend.app.core.exceptions import NotFoundError
from backend.app.models import MedicalRecord
from backend.app.repositories import MedicalRecordRepository
from backend.app.schemas.appointment import ClinicSummary, DoctorSummary
from backend.app.schemas.medical_record import (
    MedicalRecordDetail,
    MedicalRecordPage,
    MedicalRecordSummary,
    PrescriptionItemResponse,
    PrescriptionResponse,
)


class MedicalRecordService:
    def __init__(self, session: Session) -> None:
        self.repository = MedicalRecordRepository(session)

    @staticmethod
    def _doctor(record: MedicalRecord) -> DoctorSummary:
        doctor = record.appointment.doctor
        return DoctorSummary(
            doctor_id=doctor.doctor_id,
            full_name=doctor.user.full_name,
            specialty=doctor.specialty.specialty_name,
        )

    def list_records(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        keyword: str | None,
    ) -> MedicalRecordPage:
        records, total = self.repository.list_for_patient(
            patient_id, page=page, page_size=page_size, keyword=keyword
        )
        return MedicalRecordPage(
            items=[
                MedicalRecordSummary(
                    medical_record_id=record.medical_record_id,
                    appointment_id=record.appointment_id,
                    examination_date=record.examination_date,
                    diagnosis=record.diagnosis,
                    doctor=self._doctor(record),
                )
                for record in records
            ],
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
        )

    def get_detail(self, medical_record_id: int, patient_id: int) -> MedicalRecordDetail:
        record = self.repository.get_owned(medical_record_id, patient_id)
        if record is None:
            raise NotFoundError("Medical record not found.")
        clinic = record.appointment.clinic
        prescription = record.prescription
        return MedicalRecordDetail(
            medical_record_id=record.medical_record_id,
            appointment_id=record.appointment_id,
            examination_date=record.examination_date,
            symptoms=record.symptoms,
            diagnosis=record.diagnosis,
            notes=record.notes,
            doctor=self._doctor(record),
            clinic=(
                ClinicSummary(clinic_id=clinic.clinic_id, clinic_name=clinic.clinic_name)
                if clinic is not None
                else None
            ),
            prescription=(
                PrescriptionResponse(
                    prescription_id=prescription.prescription_id,
                    created_at=prescription.created_at,
                    items=[
                        PrescriptionItemResponse(
                            medicine_name=item.medicine_name,
                            quantity=item.quantity,
                            dosage=item.dosage,
                            instructions=item.instructions,
                        )
                        for item in prescription.items
                    ],
                )
                if prescription is not None
                else None
            ),
        )
