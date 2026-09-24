"""Automated security, RBAC, and business logic contract tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import get_current_user as api_get_current_user
from backend.app.deps import get_current_user as legacy_get_current_user
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.models import Appointment, Doctor, MedicalRecord, User
from backend.app.schemas.common import AppointmentStatus


@pytest.fixture
def fake_db_session() -> MagicMock:
    return MagicMock(name="mock_db_session")


def test_unauthenticated_doctor_portal_access_rejected(client: TestClient) -> None:
    """Verify that unauthenticated callers cannot access doctor endpoints."""
    # Doctor profile
    res1 = client.get("/api/v1/doctor/profile")
    assert res1.status_code in (401, 403)

    # Doctor schedule
    res2 = client.get("/api/v1/doctor/schedule?doctor_id=1")
    assert res2.status_code in (401, 403)

    # Accept patient
    res3 = client.put("/api/v1/doctor/appointments/1/accept")
    assert res3.status_code in (401, 403)

    # Complete examination
    res4 = client.post("/api/v1/doctor/appointments/1/complete", json={"symptoms": "a", "diagnosis": "b"})
    assert res4.status_code in (401, 403)


def test_patient_cannot_access_doctor_portal(client: TestClient) -> None:
    """Verify that a PATIENT role receives 403 Forbidden on doctor endpoints."""
    patient_user = SimpleNamespace(
        user_id=1,
        username="patient01",
        full_name="Nguyen Van Patient",
        role="PATIENT",
        is_active=True,
    )
    app.dependency_overrides[legacy_get_current_user] = lambda: patient_user
    app.dependency_overrides[api_get_current_user] = lambda: patient_user

    # Attempt to view doctor schedule
    res = client.get("/api/v1/doctor/schedule?doctor_id=1")
    assert res.status_code == 403
    assert "Chỉ bác sĩ hoặc quản trị viên" in res.json()["detail"]

    # Attempt to accept appointment
    res2 = client.put("/api/v1/doctor/appointments/1/accept")
    assert res2.status_code == 403

    # Attempt to complete appointment
    res3 = client.post("/api/v1/doctor/appointments/1/complete", json={"symptoms": "a", "diagnosis": "b"})
    assert res3.status_code == 403


def test_patient_cannot_access_reception_portal(client: TestClient) -> None:
    """Verify that a PATIENT role cannot access reception endpoints."""
    patient_user = SimpleNamespace(
        user_id=1,
        username="patient01",
        full_name="Nguyen Van Patient",
        role="PATIENT",
        is_active=True,
    )
    app.dependency_overrides[api_get_current_user] = lambda: patient_user

    res = client.get("/api/v1/reception/dashboard")
    assert res.status_code == 403


def test_patient_cannot_access_admin_endpoints(client: TestClient) -> None:
    """Verify that a PATIENT role cannot access /users, /doctors, /specialties admin APIs."""
    patient_user = SimpleNamespace(
        user_id=1,
        username="patient01",
        full_name="Nguyen Van Patient",
        role="PATIENT",
        is_active=True,
    )
    app.dependency_overrides[legacy_get_current_user] = lambda: patient_user

    res1 = client.get("/users/")
    assert res1.status_code == 403

    res2 = client.get("/doctors/")
    assert res2.status_code == 403

    res3 = client.get("/schedules/")
    assert res3.status_code == 403


def test_doctor_cannot_access_another_doctor_schedule(client: TestClient) -> None:
    """Verify that doctor01 cannot view doctor02's schedule."""
    doctor_user = SimpleNamespace(
        user_id=10,
        username="doctor01",
        full_name="Dr. Minh Anh",
        role="DOCTOR",
        is_active=True,
    )
    doctor_profile = SimpleNamespace(
        doctor_id=1,
        user_id=10,
        license_number="LIC-001",
        is_active=True,
    )

    mock_db = MagicMock()
    # Mock doctor profile query
    mock_db.query.return_value.filter.return_value.first.return_value = doctor_profile

    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    # Doctor 1 requests Doctor 2's schedule
    res = client.get("/api/v1/doctor/schedule?doctor_id=2")
    assert res.status_code == 403
    assert "không có quyền xem lịch làm việc của bác sĩ khác" in res.json()["detail"]


def test_doctor_cannot_complete_another_doctor_appointment(client: TestClient) -> None:
    """Verify that doctor01 cannot complete an appointment belonging to doctor02."""
    doctor_user = SimpleNamespace(
        user_id=10,
        username="doctor01",
        full_name="Dr. Minh Anh",
        role="DOCTOR",
        is_active=True,
    )
    doctor_profile = SimpleNamespace(
        doctor_id=1,
        user_id=10,
        license_number="LIC-001",
        is_active=True,
    )
    appointment = SimpleNamespace(
        appointment_id=99,
        doctor_id=2,  # Owned by doctor 2!
        status="IN_PROGRESS",
    )

    mock_db = MagicMock()
    # First query for Doctor, second query for Appointment
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor_profile
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        return m

    mock_db.query.side_effect = query_mock

    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/api/v1/doctor/appointments/99/complete",
        json={"symptoms": "Cough", "diagnosis": "Flu"},
    )
    assert res.status_code == 403
    assert "không có quyền hoàn tất ca khám của bác sĩ khác" in res.json()["detail"]


def test_cannot_complete_already_completed_appointment(client: TestClient) -> None:
    """Verify that completing a COMPLETED appointment returns 400 Bad Request."""
    doctor_user = SimpleNamespace(
        user_id=10,
        username="doctor01",
        full_name="Dr. Minh Anh",
        role="DOCTOR",
        is_active=True,
    )
    doctor_profile = SimpleNamespace(
        doctor_id=1,
        user_id=10,
        license_number="LIC-001",
        is_active=True,
    )
    appointment = SimpleNamespace(
        appointment_id=100,
        doctor_id=1,
        status="COMPLETED",
    )

    mock_db = MagicMock()
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor_profile
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        return m

    mock_db.query.side_effect = query_mock

    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/api/v1/doctor/appointments/100/complete",
        json={"symptoms": "Cough", "diagnosis": "Flu"},
    )
    assert res.status_code == 400
    assert "đã được hoàn tất trước đó" in res.json()["detail"]


def test_prescription_quantity_must_be_positive(client: TestClient) -> None:
    """Verify that quantity <= 0 in prescription item is rejected with 422 Unprocessable Entity."""
    doctor_user = SimpleNamespace(
        user_id=10,
        username="doctor01",
        full_name="Dr. Minh Anh",
        role="DOCTOR",
        is_active=True,
    )
    doctor_profile = SimpleNamespace(
        doctor_id=1,
        user_id=10,
        license_number="LIC-001",
        is_active=True,
    )
    appointment = SimpleNamespace(
        appointment_id=101,
        doctor_id=1,
        status="IN_PROGRESS",
    )

    mock_db = MagicMock()
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor_profile
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        elif model == MedicalRecord:
            m.filter.return_value.first.return_value = None
        return m

    mock_db.query.side_effect = query_mock

    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    # Send quantity = 0
    res = client.post(
        "/api/v1/doctor/appointments/101/complete",
        json={
            "symptoms": "Fever",
            "diagnosis": "Viral fever",
            "prescription_items": [
                {"medicine_name": "Paracetamol", "quantity": 0, "dosage": "500mg"}
            ],
        },
    )
    assert res.status_code == 422


def test_schedule_day_of_week_and_duration_validation(client: TestClient) -> None:
    """Verify that ScheduleCreate rejects invalid DayOfWeek (<1 or >7) and SlotDuration (<=0)."""
    admin_user = SimpleNamespace(
        user_id=999,
        username="admin",
        role="ADMIN",
        is_active=True,
    )
    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user

    # Invalid DayOfWeek = 8
    res1 = client.post(
        "/schedules/",
        json={
            "DoctorID": 1,
            "DayOfWeek": 8,
            "StartTime": "08:00:00",
            "EndTime": "12:00:00",
            "SlotDuration": 30,
        },
    )
    assert res1.status_code == 422

    # Invalid SlotDuration = -10
    res2 = client.post(
        "/schedules/",
        json={
            "DoctorID": 1,
            "DayOfWeek": 2,
            "StartTime": "08:00:00",
            "EndTime": "12:00:00",
            "SlotDuration": -10,
        },
    )
    assert res2.status_code == 422
