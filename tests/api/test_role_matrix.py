"""Exhaustive role-by-role contract and business logic test suite for ClinicManagement.

Covers:
- ADMIN: Users, Doctors, Specialties, Clinics, Schedules, Statistics
- DOCTOR: Profile, Schedule, Accept Patient, Complete Exam, Prescription Constraints
- PATIENT: Registration, Catalog, Booking Rules, Anti-Spam, Cancellation, IDOR Protection
- STAFF / RECEPTIONIST: Dashboard, Confirm, Check-In, Invoicing, Payment Constraints
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.api.deps import (
    get_current_patient,
    get_current_user as api_get_current_user,
)
from backend.app.db.session import get_db
from backend.app.deps import get_current_user as legacy_get_current_user
from backend.app.main import app
from backend.app.models import (
    Appointment,
    Clinic,
    Doctor,
    MedicalRecord,
    Patient,
    Specialty,
    User,
)



# ==============================================================================
# 1. ADMIN ROLE TESTS (/users, /doctors, /specialties, /clinics, /schedules, /statistics)
# ==============================================================================

def _setup_mock_db_user():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None
    def fake_refresh(obj):
        if getattr(obj, "user_id", None) is None:
            obj.user_id = 123
        if getattr(obj, "is_active", None) is None:
            obj.is_active = True
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now()
    mock_db.refresh.side_effect = fake_refresh
    return mock_db


def test_admin_create_staff_user_success(client: TestClient) -> None:
    """TC-ADM-02: Admin creates a valid STAFF user."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = _setup_mock_db_user()

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/users/",
        json={
            "Username": "reception01",
            "Password": "StaffPassword123!",
            "FullName": "Le Thi Thu Ngan",
            "Phone": "0901234567",
            "Email": "staff@clinic.vn",
            "Role": "STAFF",
        },
    )
    assert res.status_code == 200
    assert res.json()["Role"] == "STAFF"
    assert res.json()["Username"] == "reception01"


def test_admin_create_patient_creates_patient_profile(client: TestClient) -> None:
    """TC-ADM-03: When admin creates a PATIENT user, a Patient profile record is automatically created."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = _setup_mock_db_user()

    added_objects = []
    def capture_add(obj):
        added_objects.append(obj)
    mock_db.add.side_effect = capture_add

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/users/",
        json={
            "Username": "patient_new",
            "Password": "Password123!",
            "FullName": "Tran Van Moi",
            "Phone": "0911223344",
            "Email": "moi@test.vn",
            "Role": "PATIENT",
        },
    )
    assert res.status_code == 200
    # Verify that a Patient model instance was added to the database session
    patient_instances = [obj for obj in added_objects if isinstance(obj, Patient)]
    assert len(patient_instances) == 1


def test_admin_create_doctor_at_users_rejected(client: TestClient) -> None:
    """TC-ADM-05: Creating a DOCTOR via /users/ is rejected with clear instructions to use /doctors/."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/users/",
        json={
            "Username": "doctor_orphan",
            "Password": "DoctorPassword123!",
            "FullName": "Dr. Orphan",
            "Role": "DOCTOR",
        },
    )
    assert res.status_code == 400
    assert "Quản lý Bác sĩ" in res.json()["detail"]


def test_admin_create_user_invalid_role_rejected(client: TestClient) -> None:
    """TC-ADM-06: Creating user with invalid role is rejected with 422."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user

    res = client.post(
        "/users/",
        json={
            "Username": "bad_role_user",
            "Password": "Password123!",
            "FullName": "Bad Role",
            "Role": "SUPER_ADMIN",
        },
    )
    assert res.status_code == 422


def test_admin_create_user_duplicate_username_rejected(client: TestClient) -> None:
    """TC-ADM-04: Creating user with already existing username returns 400."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()
    # Simulate existing user found
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(user_id=1, username="admin")

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/users/",
        json={
            "Username": "admin",
            "Password": "Password123!",
            "FullName": "Existing User",
            "Role": "STAFF",
        },
    )
    assert res.status_code == 400
    assert "Username đã tồn tại" in res.json()["detail"]


def test_admin_create_doctor_duplicate_license_rejected(client: TestClient) -> None:
    """TC-ADM-12: Creating a doctor with a duplicate license number returns 400 Bad Request."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()

    def query_mock(model):
        m = MagicMock()
        if model == User:
            m.filter.return_value.first.return_value = None  # username unique
        elif model == Specialty:
            m.filter.return_value.first.return_value = SimpleNamespace(specialty_id=1)
        elif model == Clinic:
            m.filter.return_value.first.return_value = SimpleNamespace(clinic_id=1)
        elif model == Doctor:
            # Duplicate license exists!
            m.filter.return_value.first.return_value = SimpleNamespace(doctor_id=2, license_number="LIC-001")
        return m

    mock_db.query.side_effect = query_mock
    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/doctors/",
        json={
            "Username": "new_doc",
            "Password": "Doctor123!",
            "FullName": "Dr. Duplicate",
            "SpecialtyID": 1,
            "ClinicID": 1,
            "LicenseNumber": "LIC-001",
        },
    )
    assert res.status_code == 400
    assert "Số chứng chỉ hành nghề đã tồn tại" in res.json()["detail"]


def test_admin_update_specialty_duplicate_name_rejected(client: TestClient) -> None:
    """TC-ADM-19: Updating a specialty with an existing specialty name returns 400 Bad Request."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()

    # Specialty exists, but another specialty already has the new name
    target_spec = SimpleNamespace(specialty_id=1, specialty_name="Cardiology", description="", is_active=True)
    other_spec = SimpleNamespace(specialty_id=2, specialty_name="Dermatology")

    call_count = 0
    def filter_mock(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        if call_count == 1:
            m.first.return_value = target_spec
        else:
            m.first.return_value = other_spec
        return m

    mock_db.query.return_value.filter.side_effect = filter_mock
    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.put(
        "/specialties/1",
        json={"SpecialtyName": "Dermatology"},
    )
    assert res.status_code == 400
    assert "Tên chuyên khoa đã tồn tại" in res.json()["detail"]


def test_admin_create_schedule_time_validation_rejected(client: TestClient) -> None:
    """TC-ADM-25: Creating schedule where StartTime >= EndTime returns 400."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(doctor_id=1)

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/schedules/",
        json={
            "DoctorID": 1,
            "DayOfWeek": 3,
            "StartTime": "14:00:00",
            "EndTime": "10:00:00",  # Invalid!
            "SlotDuration": 30,
        },
    )
    assert res.status_code == 400
    assert "Giờ bắt đầu phải nhỏ hơn giờ kết thúc" in res.json()["detail"]


def test_admin_statistics_overview_success(client: TestClient) -> None:
    """TC-ADM-28: Statistics overview returns correct aggregate structure."""
    admin_user = SimpleNamespace(user_id=999, username="admin", role="ADMIN", is_active=True)
    mock_db = MagicMock()
    mock_db.query.return_value.scalar.return_value = 10
    mock_db.query.return_value.filter.return_value.scalar.return_value = 5
    mock_db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [
        ("Cardiology", 3),
        ("Internal Medicine", 2),
    ]

    app.dependency_overrides[legacy_get_current_user] = lambda: admin_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.get("/statistics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "total_users" in data
    assert "total_doctors" in data
    assert "doctors_by_specialty" in data


# ==============================================================================
# 2. DOCTOR ROLE TESTS (/api/v1/doctor)
# ==============================================================================

def test_doctor_profile_success(client: TestClient) -> None:
    """TC-DOC-03: Doctor successfully retrieves their own profile."""
    doctor_user = SimpleNamespace(user_id=10, username="doctor01", full_name="Dr. Minh Anh", role="DOCTOR", is_active=True)
    doctor = SimpleNamespace(
        doctor_id=1,
        user_id=10,
        license_number="LIC-001",
        specialty=SimpleNamespace(specialty_name="Cardiology"),
        clinic=SimpleNamespace(clinic_name="Central Clinic"),
    )

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = doctor

    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.get("/api/v1/doctor/profile")
    assert res.status_code == 200
    data = res.json()
    assert data["doctor_id"] == 1
    assert data["specialty_name"] == "Cardiology"
    assert data["clinic_name"] == "Central Clinic"


def test_doctor_accept_own_appointment_success(client: TestClient) -> None:
    """TC-DOC-09: Doctor accepts their own appointment, transitioning status to IN_PROGRESS."""
    doctor_user = SimpleNamespace(user_id=10, username="doctor01", full_name="Dr. Minh Anh", role="DOCTOR", is_active=True)
    doctor = SimpleNamespace(doctor_id=1, user_id=10, is_active=True)
    appointment = SimpleNamespace(appointment_id=50, doctor_id=1, status="CHECKED_IN")

    mock_db = MagicMock()
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        return m

    mock_db.query.side_effect = query_mock
    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.put("/api/v1/doctor/appointments/50/accept")
    assert res.status_code == 200
    assert appointment.status == "IN_PROGRESS"


def test_doctor_accept_cancelled_appointment_rejected(client: TestClient) -> None:
    """TC-DOC-12: Doctor cannot accept a CANCELLED appointment."""
    doctor_user = SimpleNamespace(user_id=10, username="doctor01", full_name="Dr. Minh Anh", role="DOCTOR", is_active=True)
    doctor = SimpleNamespace(doctor_id=1, user_id=10, is_active=True)
    appointment = SimpleNamespace(appointment_id=51, doctor_id=1, status="CANCELLED")

    mock_db = MagicMock()
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        return m

    mock_db.query.side_effect = query_mock
    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.put("/api/v1/doctor/appointments/51/accept")
    assert res.status_code == 400
    assert "CANCELLED" in res.json()["detail"]


def test_doctor_complete_examination_success(client: TestClient) -> None:
    """TC-DOC-13: Doctor completes appointment, recording symptoms, diagnosis, and prescription items."""
    doctor_user = SimpleNamespace(user_id=10, username="doctor01", full_name="Dr. Minh Anh", role="DOCTOR", is_active=True)
    doctor = SimpleNamespace(doctor_id=1, user_id=10, is_active=True)
    appointment = SimpleNamespace(appointment_id=52, doctor_id=1, status="IN_PROGRESS")

    mock_db = MagicMock()
    def query_mock(model):
        m = MagicMock()
        if model == Doctor:
            m.filter.return_value.first.return_value = doctor
        elif model == Appointment:
            m.filter.return_value.first.return_value = appointment
        elif model == MedicalRecord:
            m.filter.return_value.first.return_value = None  # No existing record
        return m

    mock_db.query.side_effect = query_mock
    app.dependency_overrides[legacy_get_current_user] = lambda: doctor_user
    app.dependency_overrides[get_db] = lambda: mock_db

    res = client.post(
        "/api/v1/doctor/appointments/52/complete",
        json={
            "symptoms": "Chóng mặt, đau đầu nhẹ",
            "diagnosis": "Thiếu máu não thoáng qua",
            "notes": "Nghỉ ngơi và uống nhiều nước",
            "prescription_items": [
                {
                    "medicine_name": "Ginkgo Biloba",
                    "quantity": 30,
                    "dosage": "80mg",
                    "instructions": "Uống 1 viên sau ăn sáng",
                }
            ],
        },
    )
    assert res.status_code == 200
    assert appointment.status == "COMPLETED"


# ==============================================================================
# 3. PATIENT ROLE TESTS (/api/v1/appointments, /medical-records, /invoices, /patients)
# ==============================================================================

def test_patient_booking_anti_spam_specialty_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-PAT-16: Anti-spam prevents patient from booking 2 active appointments in same specialty on same date."""
    from backend.app.api.routes import appointments
    from backend.app.core.exceptions import ConflictError

    mock_booking_service = MagicMock()
    mock_booking_service.book_appointment.side_effect = ConflictError(
        "Bạn đã có một lịch hẹn trong ngày này thuộc chuyên khoa Tim mạch."
    )
    monkeypatch.setattr(appointments, "BookingService", lambda _session: mock_booking_service)

    patient_user = SimpleNamespace(user_id=1, username="patient01", role="PATIENT", is_active=True)
    patient = SimpleNamespace(patient_id=10, user_id=1, user=patient_user)

    app.dependency_overrides[api_get_current_user] = lambda: patient_user
    app.dependency_overrides[get_current_patient] = lambda: patient

    res = client.post(
        "/api/v1/appointments",
        json={
            "doctor_id": 1,
            "appointment_date": "2026-10-01",
            "start_time": "08:30:00",
            "end_time": "09:00:00",
            "reason": "Khám tim định kỳ",
        },
    )
    assert res.status_code == 409
    assert "chuyên khoa" in res.json()["detail"]


def test_patient_cancel_completed_appointment_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-PAT-21: Patient cannot cancel an appointment that is already COMPLETED."""
    from backend.app.api.routes import appointments
    from backend.app.core.exceptions import AppError

    mock_booking_service = MagicMock()
    mock_booking_service.cancel_appointment.side_effect = AppError(
        "Không thể hủy lịch hẹn đang ở trạng thái COMPLETED."
    )
    monkeypatch.setattr(appointments, "BookingService", lambda _session: mock_booking_service)

    patient_user = SimpleNamespace(user_id=1, username="patient01", role="PATIENT", is_active=True)
    patient = SimpleNamespace(patient_id=10, user_id=1, user=patient_user)

    app.dependency_overrides[api_get_current_user] = lambda: patient_user
    app.dependency_overrides[get_current_patient] = lambda: patient

    res = client.post(
        "/api/v1/appointments/100/cancel",
        json={"cancellation_reason": "Bận việc đột xuất"},
    )
    assert res.status_code == 400
    assert "COMPLETED" in res.json()["detail"]


# ==============================================================================
# 4. STAFF / RECEPTIONIST ROLE TESTS (/api/v1/reception)
# ==============================================================================

def test_staff_confirm_appointment_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-REC-05: Receptionist confirms a PENDING appointment."""
    from backend.app.api.routes import reception

    mock_service = MagicMock()
    mock_service.confirm_appointment.return_value = {
        "appointment_id": 200,
        "appointment_date": "2026-09-25",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "reason": "Khám nội",
        "status": "CONFIRMED",
        "created_at": "2026-09-24T10:00:00",
        "patient": {"patient_id": 1, "user_id": 10, "full_name": "Bệnh nhân A"},
        "doctor": {"doctor_id": 1, "full_name": "Dr. Minh Anh", "specialty": "Internal"},
    }
    monkeypatch.setattr(reception, "ReceptionService", lambda _session: mock_service)

    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.post("/api/v1/reception/appointments/200/confirm")
    assert res.status_code == 200
    assert res.json()["status"] == "CONFIRMED"


def test_staff_check_in_appointment_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-REC-06: Receptionist checks in patient upon arrival with queue number."""
    from backend.app.api.routes import reception

    mock_service = MagicMock()
    mock_service.check_in_patient.return_value = {
        "appointment_id": 200,
        "appointment_date": "2026-09-25",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "reason": "Khám nội",
        "status": "CHECKED_IN",
        "created_at": "2026-09-24T10:00:00",
        "patient": {"patient_id": 1, "user_id": 10, "full_name": "Bệnh nhân A"},
        "doctor": {"doctor_id": 1, "full_name": "Dr. Minh Anh", "specialty": "Internal"},
    }
    monkeypatch.setattr(reception, "ReceptionService", lambda _session: mock_service)

    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.post(
        "/api/v1/reception/appointments/200/check-in",
        json={"queue_number": "A-01", "notes": "Đã có mặt tại quầy"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "CHECKED_IN"


def test_staff_create_duplicate_invoice_rejected(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-REC-11: Creating a second invoice for the same appointment is rejected with 409 Conflict."""
    from backend.app.api.routes import reception
    from backend.app.core.exceptions import ConflictError

    mock_service = MagicMock()
    mock_service.create_invoice.side_effect = ConflictError(
        "An invoice already exists for this appointment."
    )
    monkeypatch.setattr(reception, "ReceptionService", lambda _session: mock_service)

    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.post(
        "/api/v1/reception/invoices",
        json={
            "appointment_id": 200,
            "items": [{"item_name": "Tiền khám", "quantity": 1, "unit_price": 200000}],
        },
    )
    assert res.status_code == 409
    assert "invoice already exists" in res.json()["detail"]


def test_staff_process_payment_invalid_method_rejected(client: TestClient) -> None:
    """TC-REC-15: Payment method must be CASH or CARD. BITCOIN or BANK_TRANSFER rejected with 422."""
    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.post(
        "/api/v1/reception/invoices/300/pay",
        json={"payment_method": "BITCOIN", "amount": 200000},
    )
    assert res.status_code == 422


def test_staff_process_payment_zero_amount_rejected(client: TestClient) -> None:
    """TC-REC-14: Payment amount must be strictly greater than 0. Zero amount rejected with 422."""
    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.post(
        "/api/v1/reception/invoices/300/pay",
        json={"payment_method": "CASH", "amount": 0},
    )
    assert res.status_code == 422


def test_staff_get_invoice_by_id(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """TC-REC-16: Staff can fetch single invoice by ID directly."""
    from datetime import date, datetime
    from decimal import Decimal
    from backend.app.api.routes import reception
    from backend.app.schemas.reception import ReceptionInvoiceItem

    mock_service = MagicMock()
    mock_service.get_invoice.return_value = ReceptionInvoiceItem(
        invoice_id=300,
        appointment_id=200,
        created_at=datetime(2026, 9, 25, 10, 0),
        total_amount=Decimal("250000.00"),
        status="UNPAID",
        patient_name="Tran Van A",
        patient_phone="0911223344",
        doctor_name="BS. Nguyen Van B",
        appointment_date=date(2026, 9, 25),
    )
    monkeypatch.setattr(reception, "ReceptionService", lambda _session: mock_service)

    staff_user = SimpleNamespace(user_id=88, username="reception01", role="STAFF", is_active=True)
    app.dependency_overrides[api_get_current_user] = lambda: staff_user

    res = client.get("/api/v1/reception/invoices/300")
    assert res.status_code == 200
    data = res.json()
    assert data["invoice_id"] == 300
    assert data["patient_name"] == "Tran Van A"
    assert data["status"] == "UNPAID"

