"""Contract tests for catalog, booking, cancellation, and rescheduling endpoints."""

from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.schemas.appointment import (
    AppointmentDetail,
)
from backend.app.schemas.booking import (
    AvailableSlotsResponse,
    DoctorPublicItem,
    SpecialtyItem,
    TimeSlot,
)


def _sample_detail() -> dict:
    return {
        "appointment_id": 100,
        "appointment_date": "2026-10-05",
        "start_time": "08:00:00",
        "end_time": "08:30:00",
        "reason": "Routine exam",
        "status": "PENDING",
        "doctor": {
            "doctor_id": 5,
            "full_name": "Dr. Tran Van B",
            "specialty": "Cardiology",
            "phone": "0911223344",
            "email": "dr.tran@example.com",
            "license_number": "DOC-12345",
        },
        "clinic": {
            "clinic_id": 1,
            "clinic_name": "Central Clinic",
            "address": "123 Health Ave",
            "phone": "028111222",
        },
        "medical_record_id": None,
        "invoice_id": None,
    }


def test_list_specialties_contract(client: TestClient):
    with patch("backend.app.api.routes.catalog.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.list_specialties.return_value = [
            SpecialtyItem(
                specialty_id=1,
                specialty_name="Cardiology",
                description="Heart care",
                doctor_count=2,
            )
        ]

        response = client.get("/api/v1/catalog/specialties")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["specialty_name"] == "Cardiology"
        assert data[0]["doctor_count"] == 2


def test_list_doctors_contract(client: TestClient):
    with patch("backend.app.api.routes.catalog.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.list_doctors.return_value = [
            DoctorPublicItem(
                doctor_id=5,
                full_name="Dr. Tran Van B",
                specialty_id=1,
                specialty_name="Cardiology",
                clinic_id=1,
                clinic_name="Central Clinic",
            )
        ]

        response = client.get("/api/v1/catalog/doctors?specialty_id=1")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["full_name"] == "Dr. Tran Van B"


def test_get_available_slots_contract(client: TestClient):
    with patch("backend.app.api.routes.catalog.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.get_available_slots.return_value = AvailableSlotsResponse(
            doctor_id=5,
            doctor_name="Dr. Tran Van B",
            specialty_name="Cardiology",
            clinic_name="Central Clinic",
            appointment_date="2026-10-05",
            day_of_week=1,
            has_schedule=True,
            slots=[
                TimeSlot(
                    start_time="08:00:00",
                    end_time="08:30:00",
                    is_available=True,
                    reason=None,
                )
            ],
        )

        response = client.get(
            "/api/v1/catalog/doctors/5/available-slots?appointment_date=2026-10-05"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["has_schedule"] is True
        assert len(data["slots"]) == 1
        assert data["slots"][0]["is_available"] is True


def test_create_appointment_contract(authenticated_client: TestClient):
    with patch("backend.app.api.routes.appointments.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        instance.book_appointment.return_value = AppointmentDetail(**_sample_detail())

        payload = {
            "doctor_id": 5,
            "appointment_date": "2026-10-05",
            "start_time": "08:00:00",
            "end_time": "08:30:00",
            "reason": "Routine exam",
        }
        response = authenticated_client.post("/api/v1/appointments", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["appointment_id"] == 100
        assert data["status"] == "PENDING"


def test_cancel_appointment_contract(authenticated_client: TestClient):
    with patch("backend.app.api.routes.appointments.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        sample = _sample_detail()
        sample["status"] = "CANCELLED"
        instance.cancel_appointment.return_value = AppointmentDetail(**sample)

        payload = {"cancellation_reason": "Feeling better"}
        response = authenticated_client.post("/api/v1/appointments/100/cancel", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "CANCELLED"


def test_reschedule_appointment_contract(authenticated_client: TestClient):
    with patch("backend.app.api.routes.appointments.BookingService") as mock_service_cls:
        instance = mock_service_cls.return_value
        sample = _sample_detail()
        sample["appointment_date"] = "2026-10-12"
        instance.reschedule_appointment.return_value = AppointmentDetail(**sample)

        payload = {
            "new_appointment_date": "2026-10-12",
            "new_start_time": "09:00:00",
            "new_end_time": "09:30:00",
            "reason": "Rescheduled next week",
        }
        response = authenticated_client.post("/api/v1/appointments/100/reschedule", json=payload)
        assert response.status_code == 200
        assert response.json()["appointment_date"] == "2026-10-12"
