"""Public and patient catalog endpoints for specialties, doctors, and available slots."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from backend.app.api.deps import DatabaseSession, OptionalPatient
from backend.app.schemas.booking import (
    AvailableSlotsResponse,
    DoctorPublicItem,
    DoctorScheduleItem,
    SpecialtyItem,
)
from backend.app.services.booking_service import BookingService

router = APIRouter(prefix="/catalog", tags=["Catalog & Doctor Schedules"])


@router.get("/specialties", response_model=list[SpecialtyItem])
def list_specialties(session: DatabaseSession) -> list[SpecialtyItem]:
    return BookingService(session).list_specialties()


@router.get("/doctors", response_model=list[DoctorPublicItem])
def list_doctors(
    session: DatabaseSession,
    specialty_id: Annotated[int | None, Query(ge=1)] = None,
    appointment_date: Annotated[date | None, Query(description="Filter doctors with schedules on this date")] = None,
) -> list[DoctorPublicItem]:
    return BookingService(session).list_doctors(
        specialty_id=specialty_id,
        appointment_date=appointment_date,
    )


@router.get("/doctors/{doctor_id}/schedules", response_model=list[DoctorScheduleItem])
def get_doctor_schedules(doctor_id: int, session: DatabaseSession) -> list[DoctorScheduleItem]:
    return BookingService(session).get_doctor_schedules(doctor_id)


@router.get("/doctors/{doctor_id}/available-slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    doctor_id: int,
    session: DatabaseSession,
    optional_patient: OptionalPatient,
    appointment_date: Annotated[date, Query(description="Target date in YYYY-MM-DD format")],
    exclude_appointment_id: Annotated[int | None, Query(description="Exclude appointment ID for reschedule self-conflict avoidance")] = None,
) -> AvailableSlotsResponse:
    patient_id = optional_patient.patient_id if optional_patient else None
    return BookingService(session).get_available_slots(
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        patient_id=patient_id,
        exclude_appointment_id=exclude_appointment_id,
    )
