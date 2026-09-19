"""Ownership-scoped medical record queries."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import (
    Appointment,
    Doctor,
    MedicalRecord,
    Prescription,
    Specialty,
    User,
)


def _medical_load_options():
    return (
        joinedload(MedicalRecord.appointment)
        .joinedload(Appointment.doctor)
        .joinedload(Doctor.user),
        joinedload(MedicalRecord.appointment)
        .joinedload(Appointment.doctor)
        .joinedload(Doctor.specialty),
        joinedload(MedicalRecord.appointment).joinedload(Appointment.clinic),
    )


class MedicalRecordRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _apply_search(statement, keyword: str | None):
        if not keyword or not keyword.strip():
            return statement
        pattern = f"%{keyword.strip()}%"
        return statement.where(
            or_(
                MedicalRecord.diagnosis.ilike(pattern),
                MedicalRecord.symptoms.ilike(pattern),
                User.full_name.ilike(pattern),
                Specialty.specialty_name.ilike(pattern),
            )
        )

    def list_for_patient(
        self,
        patient_id: int,
        *,
        page: int,
        page_size: int,
        keyword: str | None = None,
    ) -> tuple[list[MedicalRecord], int]:
        base = (
            select(MedicalRecord)
            .join(MedicalRecord.appointment)
            .join(Appointment.doctor)
            .join(Doctor.user)
            .join(Doctor.specialty)
            .where(Appointment.patient_id == patient_id)
        )
        count_statement = (
            select(func.count(MedicalRecord.medical_record_id))
            .select_from(MedicalRecord)
            .join(MedicalRecord.appointment)
            .join(Appointment.doctor)
            .join(Doctor.user)
            .join(Doctor.specialty)
            .where(Appointment.patient_id == patient_id)
        )
        base = self._apply_search(base, keyword)
        count_statement = self._apply_search(count_statement, keyword)
        total = int(self.session.scalar(count_statement) or 0)
        statement = (
            base.options(*_medical_load_options())
            .order_by(MedicalRecord.examination_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = list(self.session.execute(statement).unique().scalars().all())
        return records, total

    def get_owned(self, medical_record_id: int, patient_id: int) -> MedicalRecord | None:
        statement = (
            select(MedicalRecord)
            .join(MedicalRecord.appointment)
            .options(
                *_medical_load_options(),
                joinedload(MedicalRecord.prescription).joinedload(Prescription.items),
            )
            .where(
                MedicalRecord.medical_record_id == medical_record_id,
                Appointment.patient_id == patient_id,
            )
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def count_for_patient(self, patient_id: int) -> int:
        statement = (
            select(func.count(MedicalRecord.medical_record_id))
            .join(MedicalRecord.appointment)
            .where(Appointment.patient_id == patient_id)
        )
        return int(self.session.scalar(statement) or 0)
