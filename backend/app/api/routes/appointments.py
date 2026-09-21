"""Current patient's appointment endpoints, booking, and schedule changes."""

from typing import Annotated

from fastapi import APIRouter, Query, status

from backend.app.api.deps import CurrentPatient, DatabaseSession
from backend.app.schemas.appointment import (
    AppointmentDetail,
    AppointmentPage,
    AppointmentSummary,
)
from backend.app.schemas.booking import (
    AppointmentCancelRequest,
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
)
from backend.app.schemas.common import AppointmentStatus
from backend.app.services import AppointmentService, BookingService

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


@router.post("", response_model=AppointmentDetail, status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreateRequest,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> AppointmentDetail:
    return BookingService(session).book_appointment(current_patient.patient_id, body)


@router.post("/{appointment_id}/cancel", response_model=AppointmentDetail)
def cancel_appointment(
    appointment_id: int,
    body: AppointmentCancelRequest,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> AppointmentDetail:
    return BookingService(session).cancel_appointment(
        appointment_id, current_patient.patient_id, body
    )


@router.post("/{appointment_id}/reschedule", response_model=AppointmentDetail)
def reschedule_appointment(
    appointment_id: int,
    body: AppointmentRescheduleRequest,
    current_patient: CurrentPatient,
    session: DatabaseSession,
) -> AppointmentDetail:
    return BookingService(session).reschedule_appointment(
        appointment_id, current_patient.patient_id, body
    )
