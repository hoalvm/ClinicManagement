"""Patient profile business logic."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.exceptions import InternalServerError
from backend.app.models import Patient
from backend.app.schemas.patient import PatientProfileResponse, PatientProfileUpdate


class PatientService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def to_profile(patient: Patient) -> PatientProfileResponse:
        return PatientProfileResponse(
            patient_id=patient.patient_id,
            username=patient.user.username,
            full_name=patient.user.full_name,
            phone=patient.user.phone,
            email=patient.user.email,
            date_of_birth=patient.date_of_birth,
            gender=patient.gender,
            address=patient.address,
        )

    def get_profile(self, patient: Patient) -> PatientProfileResponse:
        return self.to_profile(patient)

    def update_profile(
        self, patient: Patient, payload: PatientProfileUpdate
    ) -> PatientProfileResponse:
        changes = payload.model_dump(exclude_unset=True)
        for field_name in ("full_name", "phone", "email"):
            if field_name in changes:
                value = changes[field_name]
                if field_name == "email" and value is not None:
                    value = str(value)
                setattr(patient.user, field_name, value)
        for field_name in ("date_of_birth", "gender", "address"):
            if field_name in changes:
                setattr(patient, field_name, changes[field_name])

        try:
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise InternalServerError("Unable to update patient profile at this time.") from exc
        return self.to_profile(patient)
