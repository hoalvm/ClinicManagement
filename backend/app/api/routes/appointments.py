"""Current patient's read-only appointment endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.appointment import (
    AppointmentDetail,
    AppointmentPage,
    AppointmentSummary,
)
from backend.app.schemas.common import AppointmentStatus
from backend.app.services import AppointmentService

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/me", response_model=AppointmentPage)
def list_appointments(
    current_patient: CurrentPatient,
    session: DatabaseSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 10,
    keyword: Annotated[str | None, Query(max_length=200)] = None,
    status: AppointmentStatus | None = None,
) -> AppointmentPage:
    return AppointmentService(session).list_appointments(
        current_patient.patient_id,
        page=page,
        page_size=page_size,
        keyword=keyword,
        status=status.value if status is not None else None,
    )


@router.get("/me/upcoming", response_model=AppointmentSummary | None)
def get_upcoming(
    current_patient: CurrentPatient, session: DatabaseSession
) -> AppointmentSummary | None:
    return AppointmentService(session).get_upcoming(current_patient.patient_id)


@router.get("/me/{appointment_id}", response_model=AppointmentDetail)
def get_appointment_detail(
    appointment_id: int,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> AppointmentDetail:
    return AppointmentService(session).get_detail(appointment_id, current_patient.patient_id)
