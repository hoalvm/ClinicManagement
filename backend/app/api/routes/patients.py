"""Current patient profile endpoints."""

from fastapi import APIRouter

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.patient import PatientProfileResponse, PatientProfileUpdate
from backend.app.services import PatientService

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("/me", response_model=PatientProfileResponse)
def get_profile(
    current_patient: CurrentPatient, session: DatabaseSession
) -> PatientProfileResponse:
    return PatientService(session).get_profile(current_patient)


@router.patch("/me", response_model=PatientProfileResponse)
def update_profile(
    payload: PatientProfileUpdate,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> PatientProfileResponse:
    return PatientService(session).update_profile(current_patient, payload)
