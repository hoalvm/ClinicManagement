"""Persistence operations for patient profiles."""

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.models import Patient


class PatientRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: int) -> Patient | None:
        statement = (
            select(Patient).options(joinedload(Patient.user)).where(Patient.user_id == user_id)
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def get_by_id(self, patient_id: int) -> Patient | None:
        statement = (
            select(Patient)
            .options(joinedload(Patient.user))
            .where(Patient.patient_id == patient_id)
        )
        return self.session.execute(statement).unique().scalar_one_or_none()

    def add(self, patient: Patient) -> Patient:
        self.session.add(patient)
        self.session.flush()
        return patient
