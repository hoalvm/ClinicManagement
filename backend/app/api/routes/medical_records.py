"""Current patient's read-only medical record endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.medical_record import MedicalRecordDetail, MedicalRecordPage
from backend.app.services import MedicalRecordService

router = APIRouter(prefix="/medical-records", tags=["Medical Records"])


@router.get("/me", response_model=MedicalRecordPage)
def list_medical_records(
    current_patient: CurrentPatient,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
) -> MedicalRecordPage:
    return MedicalRecordService(session).list_records(
        current_patient.patient_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
    )


@router.get("/me/{medical_record_id}", response_model=MedicalRecordDetail)
def get_medical_record_detail(
    medical_record_id: int,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> MedicalRecordDetail:
    return MedicalRecordService(session).get_detail(medical_record_id, current_patient.patient_id)
