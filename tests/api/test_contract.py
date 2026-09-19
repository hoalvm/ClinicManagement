"""Patient API contract tests with SQL Server access replaced at service boundaries."""

from decimal import Decimal
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.api.routes import (
    appointments,
    auth,
    dashboard,
    invoices,
    medical_records,
    patients,
)
from backend.app.core.exceptions import AuthenticationError, ConflictError, NotFoundError

REGISTER_REQUEST = {
    "username": "patient03",
    "password": "Password123!",
    "confirm_password": "Password123!",
    "full_name": "Nguyen Van C",
    "phone": "0900000003",
    "email": "patient03@example.com",
    "date_of_birth": "2000-01-01",
    "gender": "MALE",
    "address": "Ho Chi Minh City",
}

PROFILE = {
    "patient_id": 10,
    "username": "patient01",
    "full_name": "Nguyen Van A",
    "phone": "0900000000",
    "email": "patient01@example.com",
    "date_of_birth": "2000-01-01",
    "gender": "MALE",
    "address": "Ho Chi Minh City",
}

APPOINTMENT_SUMMARY = {
    "appointment_id": 100,
    "appointment_date": "2026-09-19",
    "start_time": "09:00:00",
    "end_time": "09:30:00",
    "reason": "Follow-up",
    "status": "COMPLETED",
    "doctor": {
        "doctor_id": 3,
        "full_name": "Nguyen Van B",
        "specialty": "Internal Medicine",
    },
    "clinic": {"clinic_id": 1, "clinic_name": "Central Clinic"},
}

APPOINTMENT_DETAIL = {
    **APPOINTMENT_SUMMARY,
    "doctor": {
        **APPOINTMENT_SUMMARY["doctor"],
        "phone": "0900000001",
        "email": "doctor@example.com",
        "license_number": "LIC-003",
    },
    "clinic": {
        **APPOINTMENT_SUMMARY["clinic"],
        "address": "1 Clinic Street",
        "phone": "0280000000",
    },
    "medical_record_id": 200,
    "invoice_id": 300,
}

MEDICAL_SUMMARY = {
    "medical_record_id": 200,
    "appointment_id": 100,
    "examination_date": "2026-09-19T09:45:00",
    "diagnosis": "Acute pharyngitis",
    "doctor": APPOINTMENT_SUMMARY["doctor"],
}

MEDICAL_DETAIL = {
    **MEDICAL_SUMMARY,
    "symptoms": "Sore throat",
    "notes": "Rest and drink water",
    "clinic": APPOINTMENT_SUMMARY["clinic"],
    "prescription": {
        "prescription_id": 55,
        "created_at": "2026-09-19T09:50:00",
        "items": [
            {
                "medicine_name": "Paracetamol",
                "quantity": 10,
                "dosage": "500 mg",
                "instructions": "Twice daily after meals",
            }
        ],
    },
}

INVOICE_SUMMARY = {
    "invoice_id": 300,
    "appointment_id": 100,
    "created_at": "2026-09-19T10:00:00",
    "total_amount": 450000.00,
    "status": "PAID",
}

INVOICE_DETAIL = {
    **INVOICE_SUMMARY,
    "appointment": {
        "appointment_date": "2026-09-19",
        "start_time": "09:00:00",
        "doctor": {"doctor_id": 3, "full_name": "Nguyen Van B"},
    },
    "items": [
        {
            "item_name": "Consultation",
            "quantity": 1,
            "unit_price": 200000.00,
            "line_total": 200000.00,
        }
    ],
    "payment": {
        "payment_id": 400,
        "amount": 450000.00,
        "payment_method": "CARD",
        "payment_date": "2026-09-19T10:05:00",
    },
}


def patch_service(
    monkeypatch: pytest.MonkeyPatch,
    route_module: ModuleType,
    service_name: str,
) -> MagicMock:
    service = MagicMock(name=f"mock_{service_name}")
    monkeypatch.setattr(route_module, service_name, lambda _session: service)
    return service


def test_health_check_does_not_require_authentication(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_register_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = patch_service(monkeypatch, auth, "AuthService")
    service.register.return_value = {
        "user_id": 3,
        "patient_id": 30,
        "username": "patient03",
        "full_name": "Nguyen Van C",
        "role": "PATIENT",
    }

    response = client.post("/api/v1/auth/register", json=REGISTER_REQUEST)

    assert response.status_code == 201
    assert response.json()["role"] == "PATIENT"
    payload = service.register.call_args.args[0]
    assert payload.username == "patient03"
    assert payload.confirm_password == "Password123!"


def test_register_duplicate_username_returns_conflict(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, auth, "AuthService")
    service.register.side_effect = ConflictError("Username is already registered.")

    response = client.post("/api/v1/auth/register", json=REGISTER_REQUEST)

    assert response.status_code == 409
    assert response.json() == {"detail": "Username is already registered."}


def test_custom_request_validator_returns_json_safe_422(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, auth, "AuthService")
    payload = {**REGISTER_REQUEST, "confirm_password": "DifferentPassword123!"}

    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == [
        {
            "type": "value_error",
            "loc": ["body"],
            "msg": "Value error, Passwords do not match",
        }
    ]
    service.register.assert_not_called()


def test_login_success_returns_bearer_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, auth, "AuthService")
    service.login.return_value = {"access_token": "signed-token", "token_type": "bearer"}

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "patient01", "password": "Password123!"},
    )

    assert response.status_code == 200
    assert response.json() == {"access_token": "signed-token", "token_type": "bearer"}


def test_wrong_password_returns_unauthorized(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, auth, "AuthService")
    service.login.side_effect = AuthenticationError("Incorrect username or password.")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "patient01", "password": "WrongPassword!"},
    )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Incorrect username or password."}


def test_auth_me_returns_current_user(
    authenticated_client: TestClient,
) -> None:
    response = authenticated_client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": 1,
        "patient_id": 10,
        "username": "patient01",
        "full_name": "Nguyen Van A",
        "phone": "0900000000",
        "email": "patient01@example.com",
        "role": "PATIENT",
        "is_active": True,
    }


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/auth/me",
        "/api/v1/patients/me",
        "/api/v1/appointments/me",
        "/api/v1/medical-records/me",
        "/api/v1/invoices/me",
        "/api/v1/dashboard/me",
    ],
)
def test_protected_api_without_jwt_returns_unauthorized(client: TestClient, path: str) -> None:
    response = client.get(path)

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_get_patient_profile(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, patients, "PatientService")
    service.get_profile.return_value = PROFILE

    response = authenticated_client.get("/api/v1/patients/me")

    assert response.status_code == 200
    assert response.json() == PROFILE
    assert service.get_profile.call_args.args[0].patient_id == 10


def test_update_patient_profile(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, patients, "PatientService")
    service.update_profile.return_value = {**PROFILE, "full_name": "Updated Name"}

    response = authenticated_client.patch(
        "/api/v1/patients/me",
        json={"full_name": "Updated Name", "address": "Updated Address"},
    )

    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated Name"
    patient, payload = service.update_profile.call_args.args
    assert patient.patient_id == 10
    assert payload.full_name == "Updated Name"
    assert payload.address == "Updated Address"


def test_appointment_history_pagination_search_and_status_filter(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, appointments, "AppointmentService")
    service.list_appointments.return_value = {
        "items": [APPOINTMENT_SUMMARY],
        "page": 2,
        "page_size": 5,
        "total": 6,
        "total_pages": 2,
    }

    response = authenticated_client.get(
        "/api/v1/appointments/me",
        params={
            "page": 2,
            "page_size": 5,
            "keyword": "Internal",
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 2
    assert body["total_pages"] == 2
    assert body["items"][0]["doctor"]["specialty"] == "Internal Medicine"
    service.list_appointments.assert_called_once_with(
        10,
        page=2,
        page_size=5,
        keyword="Internal",
        status="COMPLETED",
    )


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page_size": 0},
        {"page_size": 101},
        {"status": "SCHEDULED"},
    ],
)
def test_appointment_query_validation(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    params: dict[str, object],
) -> None:
    service = patch_service(monkeypatch, appointments, "AppointmentService")

    response = authenticated_client.get("/api/v1/appointments/me", params=params)

    assert response.status_code == 422
    service.list_appointments.assert_not_called()


def test_upcoming_appointment(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, appointments, "AppointmentService")
    service.get_upcoming.return_value = {**APPOINTMENT_SUMMARY, "status": "CONFIRMED"}

    response = authenticated_client.get("/api/v1/appointments/me/upcoming")

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    service.get_upcoming.assert_called_once_with(10)


def test_no_upcoming_appointment_returns_null(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, appointments, "AppointmentService")
    service.get_upcoming.return_value = None

    response = authenticated_client.get("/api/v1/appointments/me/upcoming")

    assert response.status_code == 200
    assert response.json() is None


def test_appointment_detail(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, appointments, "AppointmentService")
    service.get_detail.return_value = APPOINTMENT_DETAIL

    response = authenticated_client.get("/api/v1/appointments/me/100")

    assert response.status_code == 200
    assert response.json()["medical_record_id"] == 200
    assert response.json()["invoice_id"] == 300
    service.get_detail.assert_called_once_with(100, 10)


def test_medical_history_search_and_pagination(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, medical_records, "MedicalRecordService")
    service.list_records.return_value = {
        "items": [MEDICAL_SUMMARY],
        "page": 2,
        "page_size": 5,
        "total": 7,
        "total_pages": 2,
    }

    response = authenticated_client.get(
        "/api/v1/medical-records/me",
        params={"page": 2, "page_size": 5, "keyword": "pharyngitis"},
    )

    assert response.status_code == 200
    assert response.json()["items"][0]["diagnosis"] == "Acute pharyngitis"
    service.list_records.assert_called_once_with(
        10,
        page=2,
        page_size=5,
        keyword="pharyngitis",
    )


def test_medical_result_loads_prescription(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, medical_records, "MedicalRecordService")
    service.get_detail.return_value = MEDICAL_DETAIL

    response = authenticated_client.get("/api/v1/medical-records/me/200")

    assert response.status_code == 200
    body = response.json()
    assert body["appointment_id"] == 100
    assert body["prescription"]["items"][0]["medicine_name"] == "Paracetamol"
    service.get_detail.assert_called_once_with(200, 10)


def test_invoice_history_filter_and_pagination(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, invoices, "InvoiceService")
    service.list_invoices.return_value = {
        "items": [INVOICE_SUMMARY],
        "page": 2,
        "page_size": 5,
        "total": 6,
        "total_pages": 2,
    }

    response = authenticated_client.get(
        "/api/v1/invoices/me",
        params={"page": 2, "page_size": 5, "status": "PAID"},
    )

    assert response.status_code == 200
    total_amount = response.json()["items"][0]["total_amount"]
    assert isinstance(total_amount, int | float) and not isinstance(total_amount, bool)
    assert Decimal(str(total_amount)) == Decimal("450000.00")
    service.list_invoices.assert_called_once_with(
        10,
        page=2,
        page_size=5,
        status="PAID",
    )


def test_invoice_detail_items_and_payment(
    authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = patch_service(monkeypatch, invoices, "InvoiceService")
    service.get_detail.return_value = INVOICE_DETAIL

    response = authenticated_client.get("/api/v1/invoices/me/300")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["items"][0]["line_total"], int | float)
    assert Decimal(body["items"][0]["line_total"]) == Decimal("200000.00")
    assert body["payment"]["payment_method"] == "CARD"
    assert isinstance(body["payment"]["amount"], int | float)
    assert Decimal(body["payment"]["amount"]) == Decimal("450000.00")
    service.get_detail.assert_called_once_with(300, 10)


def test_invoice_money_fields_are_documented_as_json_numbers(client: TestClient) -> None:
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert schemas["InvoiceSummary"]["properties"]["total_amount"]["type"] == "number"
    assert schemas["InvoiceItemResponse"]["properties"]["unit_price"]["type"] == "number"
    assert schemas["InvoiceItemResponse"]["properties"]["line_total"]["type"] == "number"
    assert schemas["PaymentResponse"]["properties"]["amount"]["type"] == "number"


def test_dashboard(authenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    service = patch_service(monkeypatch, dashboard, "DashboardService")
    service.get_dashboard.return_value = {
        "patient_name": "Nguyen Van A",
        "total_appointments": 8,
        "total_medical_records": 5,
        "total_invoices": 4,
        "unpaid_invoices": 1,
        "upcoming_appointment": {**APPOINTMENT_SUMMARY, "status": "CONFIRMED"},
    }

    response = authenticated_client.get("/api/v1/dashboard/me")

    assert response.status_code == 200
    assert response.json()["total_appointments"] == 8
    assert response.json()["unpaid_invoices"] == 1
    assert response.json()["upcoming_appointment"]["appointment_id"] == 100
    assert service.get_dashboard.call_args.args[0].patient_id == 10


@pytest.mark.parametrize(
    ("route_module", "service_name", "method_name", "path", "detail"),
    [
        (
            appointments,
            "AppointmentService",
            "get_detail",
            "/api/v1/appointments/me/999",
            "Appointment not found.",
        ),
        (
            medical_records,
            "MedicalRecordService",
            "get_detail",
            "/api/v1/medical-records/me/999",
            "Medical record not found.",
        ),
        (
            invoices,
            "InvoiceService",
            "get_detail",
            "/api/v1/invoices/me/999",
            "Invoice not found.",
        ),
    ],
)
def test_patient_a_cannot_read_patient_b_resource(
    authenticated_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    route_module: ModuleType,
    service_name: str,
    method_name: str,
    path: str,
    detail: str,
) -> None:
    service = patch_service(monkeypatch, route_module, service_name)
    method = getattr(service, method_name)
    method.side_effect = NotFoundError(detail)

    response = authenticated_client.get(path)

    assert response.status_code == 404
    assert response.json() == {"detail": detail}
    method.assert_called_once_with(999, 10)
