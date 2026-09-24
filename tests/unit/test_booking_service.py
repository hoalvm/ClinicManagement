"""Unit tests for patient self-service booking, available slots, cancel, and reschedule."""

from __future__ import annotations

from datetime import date, time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.core.exceptions import AppError, ConflictError
from backend.app.schemas.booking import (
    AppointmentCancelRequest,
    AppointmentCreateRequest,
    AppointmentRescheduleRequest,
)
from backend.app.services.booking_service import BookingService


def _doctor_stub(**overrides: object) -> SimpleNamespace:
    values = {
        "doctor_id": 5,
        "user_id": 20,
        "specialty_id": 2,
        "clinic_id": 1,
        "license_number": "DOC-12345",
        "is_active": True,
        "user": SimpleNamespace(
            full_name="Dr. Tran Van B",
            phone="0911223344",
            email="dr.tran@example.com",
        ),
        "specialty": SimpleNamespace(specialty_id=2, specialty_name="Cardiology"),
        "clinic": SimpleNamespace(
            clinic_id=1,
            clinic_name="Central Clinic",
            address="123 Health Ave",
        ),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _schedule_stub(**overrides: object) -> SimpleNamespace:
    values = {
        "schedule_id": 1,
        "doctor_id": 5,
        "day_of_week": 1,  # Monday
        "start_time": time(8, 0),
        "end_time": time(10, 0),
        "slot_duration": 30,
        "is_active": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _appointment_stub(**overrides: object) -> SimpleNamespace:
    values = {
        "appointment_id": 100,
        "patient_id": 10,
        "doctor_id": 5,
        "clinic_id": 1,
        "appointment_date": date(2026, 10, 5),  # A Monday
        "start_time": time(8, 0),
        "end_time": time(8, 30),
        "reason": "Regular checkup",
        "status": "PENDING",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_list_specialties_success():
    session = MagicMock()
    service = BookingService(session)
    spec = SimpleNamespace(
        specialty_id=1,
        specialty_name="Pediatrics",
        description="Child care",
    )
    service.doctor_repo.list_specialties = MagicMock(return_value=[(spec, 3)])

    result = service.list_specialties()
    assert len(result) == 1
    assert result[0].specialty_name == "Pediatrics"
    assert result[0].doctor_count == 3


def test_list_doctors_success():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub()
    service.doctor_repo.list_doctors = MagicMock(return_value=[doc])

    result = service.list_doctors(specialty_id=2)
    assert len(result) == 1
    assert result[0].full_name == "Dr. Tran Van B"
    assert result[0].clinic_name == "Central Clinic"


def test_get_available_slots_calculation():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub()
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    # 2026-10-05 is a Monday (isoweekday = 1)
    target_date = date(2026, 10, 5)
    schedule = _schedule_stub(
        day_of_week=1, start_time=time(8, 0), end_time=time(9, 30), slot_duration=30
    )
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])

    # One existing appointment for doctor at 08:30 - 09:00
    existing = _appointment_stub(
        appointment_date=target_date,
        start_time=time(8, 30),
        end_time=time(9, 0),
    )
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[existing])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])

    slots_resp = service.get_available_slots(5, target_date, patient_id=10)
    assert slots_resp.has_schedule is True
    assert len(slots_resp.slots) == 3  # 08:00-08:30, 08:30-09:00, 09:00-09:30

    assert slots_resp.slots[0].is_available is True
    assert slots_resp.slots[1].is_available is False
    assert slots_resp.slots[1].reason == "Bác sĩ đã có lịch hẹn"
    assert slots_resp.slots[2].is_available is True


def test_book_appointment_success():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub()
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])

    def mock_add(appt):
        appt.appointment_id = 999
        return appt

    service.appointment_repo.add = MagicMock(side_effect=mock_add)
    service.appointment_service.get_detail = MagicMock(
        return_value={"appointment_id": 999, "status": "PENDING"}
    )

    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
        reason="Heart consultation",
    )

    result = service.book_appointment(10, req)
    assert result["appointment_id"] == 999
    service.appointment_repo.add.assert_called_once()


def test_book_appointment_conflict_raises():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub()
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])

    conflict_appt = _appointment_stub(
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(
        return_value=[conflict_appt]
    )
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])

    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )

    with pytest.raises(ConflictError) as exc:
        service.book_appointment(10, req)
    assert "đã có người đặt" in exc.value.detail


def test_cancel_appointment_success():
    session = MagicMock()
    service = BookingService(session)
    appt = _appointment_stub(
        status="PENDING", appointment_date=date(2026, 10, 5), start_time=time(9, 0)
    )
    service.appointment_repo.get_owned = MagicMock(return_value=appt)
    service.appointment_service.get_detail = MagicMock(
        return_value={"appointment_id": 100, "status": "CANCELLED"}
    )

    req = AppointmentCancelRequest(cancellation_reason="Busy with exam")
    result = service.cancel_appointment(100, 10, req)

    assert result["status"] == "CANCELLED"
    assert appt.status == "CANCELLED"
    assert "Busy with exam" in appt.reason


def test_cancel_appointment_invalid_status_raises():
    session = MagicMock()
    service = BookingService(session)
    appt = _appointment_stub(status="COMPLETED", appointment_date=date(2026, 10, 5))
    service.appointment_repo.get_owned = MagicMock(return_value=appt)

    req = AppointmentCancelRequest(cancellation_reason="Too late")
    with pytest.raises(AppError) as exc:
        service.cancel_appointment(100, 10, req)
    assert "Không thể hủy" in exc.value.detail


def test_reschedule_appointment_success():
    session = MagicMock()
    service = BookingService(session)
    appt = _appointment_stub(
        status="CONFIRMED",
        appointment_date=date(2026, 10, 5),
        start_time=time(8, 0),
        end_time=time(8, 30),
    )
    service.appointment_repo.get_owned = MagicMock(return_value=appt)

    new_date = date(2026, 10, 12)  # another Monday
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])
    service.appointment_service.get_detail = MagicMock(
        return_value={"appointment_id": 100, "appointment_date": str(new_date)}
    )

    req = AppointmentRescheduleRequest(
        new_appointment_date=new_date,
        new_start_time=time(9, 0),
        new_end_time=time(9, 30),
        reason="Dời lịch sang tuần sau",
    )

    service.reschedule_appointment(100, 10, req)
    assert appt.appointment_date == new_date
    assert appt.start_time == time(9, 0)
    assert appt.end_time == time(9, 30)
    assert appt.status == "PENDING"
    assert "Dời lịch sang tuần sau" in appt.reason


def test_book_appointment_fails_when_patient_has_active_same_specialty():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub(doctor_id=5, specialty_id=1, clinic_id=1)
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])

    existing_doc = _doctor_stub(doctor_id=9, specialty_id=1, clinic_id=2)
    active_appt = _appointment_stub(
        status="PENDING",
        appointment_date=future_monday,
        start_time=time(10, 0),
        end_time=time(10, 30),
        doctor=existing_doc,
    )
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(
        return_value=[active_appt]
    )

    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )

    with pytest.raises(ConflictError) as exc:
        service.book_appointment(10, req)
    assert "thuộc chuyên khoa" in exc.value.detail


def test_book_appointment_succeeds_different_specialty():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub(doctor_id=5, specialty_id=2, clinic_id=1)
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])

    # Patient has active appointment in specialty 1 (e.g. Cardiology), now booking specialty 2 (e.g. Dermatology)
    other_doc = _doctor_stub(doctor_id=9, specialty_id=1, clinic_id=2)
    active_appt = _appointment_stub(
        status="PENDING",
        appointment_date=future_monday,
        clinic_id=2,
        start_time=time(14, 0),
        end_time=time(14, 30),
        doctor=other_doc,
    )
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(
        return_value=[active_appt]
    )
    service.appointment_repo.add = MagicMock(
        side_effect=lambda a: setattr(a, "appointment_id", 888) or a
    )
    service.appointment_service.get_detail = MagicMock(return_value={"appointment_id": 888})

    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )

    result = service.book_appointment(10, req)
    assert result["appointment_id"] == 888


def test_book_appointment_fails_same_clinic_same_day():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub(doctor_id=5, specialty_id=2, clinic_id=1)
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])

    # Patient already has an appointment at clinic 1 on future_monday (even with different specialty/doctor)
    existing_doc = _doctor_stub(doctor_id=9, specialty_id=3, clinic_id=1)
    active_appt = _appointment_stub(
        status="PENDING",
        appointment_date=future_monday,
        clinic_id=1,
        start_time=time(10, 0),
        end_time=time(10, 30),
        doctor=existing_doc,
    )
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(
        return_value=[active_appt]
    )

    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )

    with pytest.raises(ConflictError) as exc:
        service.book_appointment(10, req)
    assert "phòng khám này trong ngày đã chọn" in exc.value.detail


def test_list_doctors_with_appointment_date_filter():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub()
    service.doctor_repo.list_doctors = MagicMock(return_value=[doc])

    # 2026-10-05 is Monday -> day_of_week = 1
    result = service.list_doctors(specialty_id=2, appointment_date=date(2026, 10, 5))
    service.doctor_repo.list_doctors.assert_called_once_with(2, day_of_week=1)
    assert len(result) == 1
    assert result[0].doctor_id == 5


def test_get_available_slots_excludes_self_on_reschedule():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub(doctor_id=5, specialty_id=2, clinic_id=1)
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(9, 0), slot_duration=30)
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])

    # Appointment 100 is the appointment being rescheduled at 8:00
    appt_100 = _appointment_stub(
        appointment_id=100,
        doctor_id=5,
        appointment_date=future_monday,
        start_time=time(8, 0),
        end_time=time(8, 30),
        doctor=doc,
    )
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[appt_100])
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(return_value=[appt_100])

    # When exclude_appointment_id=100, the 8:00 slot is NOT occupied by appt_100
    result = service.get_available_slots(
        doctor_id=5,
        appointment_date=future_monday,
        patient_id=10,
        exclude_appointment_id=100,
    )
    assert result.has_schedule is True
    assert len(result.slots) == 2
    # 8:00 slot is available because appt 100 was excluded
    assert result.slots[0].start_time == time(8, 0)
    assert result.slots[0].is_available is True


def test_reschedule_appointment_allows_changing_doctor():
    session = MagicMock()
    service = BookingService(session)

    old_doc = _doctor_stub(doctor_id=5, specialty_id=2, clinic_id=1)
    new_doc = _doctor_stub(doctor_id=6, specialty_id=2, clinic_id=2)

    appt = _appointment_stub(
        appointment_id=100,
        doctor_id=5,
        clinic_id=1,
        status="PENDING",
        doctor=old_doc,
    )
    service.appointment_repo.get_owned = MagicMock(return_value=appt)
    service.doctor_repo.get_doctor_by_id = MagicMock(
        side_effect=lambda doc_id: new_doc if doc_id == 6 else old_doc
    )

    future_monday = date(2026, 10, 5)
    schedule = _schedule_stub(
        doctor_id=6,
        day_of_week=1,
        start_time=time(9, 0),
        end_time=time(12, 0),
    )
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(return_value=[appt])
    service.appointment_service.get_detail = MagicMock(
        return_value={"appointment_id": 100, "status": "PENDING"}
    )

    req = AppointmentRescheduleRequest(
        new_appointment_date=future_monday,
        new_start_time=time(9, 0),
        new_end_time=time(9, 30),
        new_doctor_id=6,
    )

    result = service.reschedule_appointment(100, 10, req)
    assert result["appointment_id"] == 100
    assert appt.doctor_id == 6
    assert appt.clinic_id == 2
    assert appt.appointment_date == future_monday
    assert appt.start_time == time(9, 0)
    assert appt.end_time == time(9, 30)
    assert appt.status == "PENDING"


def test_book_appointment_succeeds_same_specialty_different_date():
    session = MagicMock()
    service = BookingService(session)
    doc = _doctor_stub(doctor_id=5, specialty_id=1, clinic_id=1)
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doc)

    date_1 = date(2026, 10, 5)  # Monday
    date_2 = date(2026, 10, 12)  # Next Monday

    schedule = _schedule_stub(day_of_week=1, start_time=time(8, 0), end_time=time(12, 0))
    service.doctor_repo.get_schedules = MagicMock(return_value=[schedule])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])

    # Patient has active appointment in same specialty on date_1
    existing_doc = _doctor_stub(doctor_id=9, specialty_id=1, clinic_id=2)
    active_appt = _appointment_stub(
        status="PENDING",
        appointment_date=date_1,
        clinic_id=2,
        start_time=time(10, 0),
        end_time=time(10, 30),
        doctor=existing_doc,
    )
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(
        return_value=[active_appt]
    )
    service.appointment_repo.add = MagicMock(
        side_effect=lambda a: setattr(a, "appointment_id", 999) or a
    )
    service.appointment_service.get_detail = MagicMock(return_value={"appointment_id": 999})

    # Booking same specialty on date_2 is allowed because the limit is 1 per day
    req = AppointmentCreateRequest(
        doctor_id=5,
        appointment_date=date_2,
        start_time=time(8, 0),
        end_time=time(8, 30),
    )

    result = service.book_appointment(10, req)
    assert result["appointment_id"] == 999


def test_reschedule_appointment_fails_for_identical_slot():
    session = MagicMock()
    service = BookingService(session)

    doc = _doctor_stub(doctor_id=5, specialty_id=2, clinic_id=1)
    appt = _appointment_stub(
        appointment_id=100,
        doctor_id=5,
        clinic_id=1,
        appointment_date=date(2026, 10, 5),
        start_time=time(8, 0),
        end_time=time(8, 30),
        status="CONFIRMED",
        doctor=doc,
    )
    service.appointment_repo.get_owned = MagicMock(return_value=appt)

    # Trying to reschedule to identical doctor, date, and time
    req = AppointmentRescheduleRequest(
        new_appointment_date=date(2026, 10, 5),
        new_start_time=time(8, 0),
        new_end_time=time(8, 30),
        new_doctor_id=5,
    )

    with pytest.raises(AppError) as exc:
        service.reschedule_appointment(100, 10, req)
    assert "khác với lịch hẹn hiện tại" in exc.value.detail


