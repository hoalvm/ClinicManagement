"""Opt-in end-to-end API checks against the seeded Microsoft SQL Server database.

Run with ``RUN_SQLSERVER_INTEGRATION=1 pytest -q tests/integration``.  Every
request gets a real SQLAlchemy session bound to one connection.  Application
``commit()`` calls only release a savepoint; the outer transaction is rolled
back after each test so the development database is not changed.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.session import engine, get_db
from backend.app.main import app

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SQLSERVER_INTEGRATION", "").strip() != "1",
        reason="set RUN_SQLSERVER_INTEGRATION=1 to use the configured SQL Server",
    ),
]

DEMO_PASSWORD = "Password123!"


@pytest.fixture
def sqlserver_client() -> Generator[TestClient, None, None]:
    """Serve the real app while containing writes in a rollback-only transaction."""

    connection = engine.connect()
    if connection.dialect.name != "mssql" or connection.dialect.driver != "pyodbc":
        connection.close()
        pytest.fail("Integration tests require Microsoft SQL Server through pyodbc")

    outer_transaction = connection.begin()
    database_name = connection.exec_driver_sql("SELECT DB_NAME()").scalar_one()
    if str(database_name).lower() in {"master", "model", "msdb", "tempdb"}:
        outer_transaction.rollback()
        connection.close()
        pytest.fail("Refusing to run integration tests against a SQL Server system database")

    request_sessions = sessionmaker(
        bind=connection,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    def override_get_db() -> Generator[Session, None, None]:
        session = request_sessions()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    previous_overrides = app.dependency_overrides.copy()
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db] = override_get_db
    outer_was_active = False

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)
        outer_was_active = outer_transaction.is_active
        if outer_was_active:
            outer_transaction.rollback()
        connection.close()
        if not outer_was_active:
            pytest.fail(
                "The app escaped the integration test's outer transaction; "
                "database rollback could not be guaranteed"
            )


def _login(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    return {"Authorization": f"Bearer {payload['access_token']}"}


def _get_page(
    client: TestClient,
    path: str,
    headers: dict[str, str],
    **params: str | int,
) -> dict[str, object]:
    response = client.get(
        path,
        headers=headers,
        params={"page": 1, "page_size": 100, **params},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["page"] == 1
    assert payload["page_size"] == 100
    assert payload["total"] == len(payload["items"])
    return payload


def _get_detail(
    client: TestClient,
    path: str,
    resource_id: int,
    headers: dict[str, str],
) -> dict[str, object]:
    response = client.get(f"{path}/{resource_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_patient01_seeded_read_flow_uses_real_sql_server(
    sqlserver_client: TestClient,
) -> None:
    headers = _login(sqlserver_client, "patient01")

    current_user_response = sqlserver_client.get("/api/v1/auth/me", headers=headers)
    assert current_user_response.status_code == 200, current_user_response.text
    current_user = current_user_response.json()
    assert current_user["username"] == "patient01"
    assert current_user["role"] == "PATIENT"
    assert current_user["patient_id"] is not None

    dashboard_response = sqlserver_client.get("/api/v1/dashboard/me", headers=headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["patient_name"] == current_user["full_name"]

    appointments = _get_page(sqlserver_client, "/api/v1/appointments/me", headers)
    appointment_items = appointments["items"]
    assert isinstance(appointment_items, list) and appointment_items
    assert dashboard["total_appointments"] == appointments["total"]

    upcoming_response = sqlserver_client.get("/api/v1/appointments/me/upcoming", headers=headers)
    assert upcoming_response.status_code == 200, upcoming_response.text
    upcoming = upcoming_response.json()
    assert upcoming is not None
    assert upcoming["status"] in {"PENDING", "CONFIRMED"}

    completed = _get_page(
        sqlserver_client,
        "/api/v1/appointments/me",
        headers,
        status="COMPLETED",
    )
    completed_items = completed["items"]
    assert isinstance(completed_items, list) and completed_items
    assert all(item["status"] == "COMPLETED" for item in completed_items)

    medical_records = _get_page(sqlserver_client, "/api/v1/medical-records/me", headers)
    medical_items = medical_records["items"]
    assert isinstance(medical_items, list) and medical_items
    assert dashboard["total_medical_records"] == medical_records["total"]

    prescription_detail = None
    for item in medical_items:
        detail = _get_detail(
            sqlserver_client,
            "/api/v1/medical-records/me",
            item["medical_record_id"],
            headers,
        )
        if detail["prescription"] and detail["prescription"]["items"]:
            prescription_detail = detail
            break

    assert prescription_detail is not None
    prescription = prescription_detail["prescription"]
    assert prescription["prescription_id"] > 0
    assert all(item["medicine_name"] for item in prescription["items"])
    assert all(item["quantity"] > 0 for item in prescription["items"])

    appointment_detail = _get_detail(
        sqlserver_client,
        "/api/v1/appointments/me",
        prescription_detail["appointment_id"],
        headers,
    )
    assert appointment_detail["medical_record_id"] == prescription_detail["medical_record_id"]
    assert appointment_detail["doctor"]["full_name"]
    assert appointment_detail["doctor"]["specialty"]

    invoices = _get_page(sqlserver_client, "/api/v1/invoices/me", headers)
    invoice_items = invoices["items"]
    assert isinstance(invoice_items, list) and invoice_items
    assert dashboard["total_invoices"] == invoices["total"]

    paid_invoices = _get_page(
        sqlserver_client,
        "/api/v1/invoices/me",
        headers,
        status="PAID",
    )
    paid_items = paid_invoices["items"]
    assert isinstance(paid_items, list) and paid_items
    paid_detail = _get_detail(
        sqlserver_client,
        "/api/v1/invoices/me",
        paid_items[0]["invoice_id"],
        headers,
    )
    assert paid_detail["items"]
    assert sum(Decimal(item["line_total"]) for item in paid_detail["items"]) == Decimal(
        paid_detail["total_amount"]
    )
    assert paid_detail["payment"] is not None
    assert paid_detail["payment"]["payment_method"] in {"CASH", "CARD"}
    assert Decimal(paid_detail["payment"]["amount"]) == Decimal(paid_detail["total_amount"])

    unpaid_invoices = _get_page(
        sqlserver_client,
        "/api/v1/invoices/me",
        headers,
        status="UNPAID",
    )
    unpaid_items = unpaid_invoices["items"]
    assert isinstance(unpaid_items, list) and unpaid_items
    unpaid_detail = _get_detail(
        sqlserver_client,
        "/api/v1/invoices/me",
        unpaid_items[0]["invoice_id"],
        headers,
    )
    assert unpaid_detail["payment"] is None
    assert dashboard["unpaid_invoices"] == unpaid_invoices["total"]


def test_patient01_gets_404_for_patient02_resource_ids(
    sqlserver_client: TestClient,
) -> None:
    patient01_headers = _login(sqlserver_client, "patient01")
    patient02_headers = _login(sqlserver_client, "patient02")

    resource_specs = (
        ("/api/v1/appointments/me", "appointment_id"),
        ("/api/v1/medical-records/me", "medical_record_id"),
        ("/api/v1/invoices/me", "invoice_id"),
    )
    for path, id_field in resource_specs:
        patient02_page = _get_page(sqlserver_client, path, patient02_headers)
        patient02_items = patient02_page["items"]
        assert isinstance(patient02_items, list) and patient02_items
        patient02_id = patient02_items[0][id_field]

        owned_response = sqlserver_client.get(f"{path}/{patient02_id}", headers=patient02_headers)
        assert owned_response.status_code == 200, owned_response.text

        hidden_response = sqlserver_client.get(f"{path}/{patient02_id}", headers=patient01_headers)
        assert hidden_response.status_code == 404, hidden_response.text
        assert "not found" in hidden_response.json()["detail"].lower()


def test_profile_update_persists_across_request_scoped_sessions(
    sqlserver_client: TestClient,
) -> None:
    headers = _login(sqlserver_client, "patient01")
    original_response = sqlserver_client.get("/api/v1/patients/me", headers=headers)
    assert original_response.status_code == 200, original_response.text
    original = original_response.json()

    suffix = uuid4().hex[:12]
    expected_full_name = f"Integration {suffix}"
    expected_address = f"Rollback probe {suffix}"
    update_response = sqlserver_client.patch(
        "/api/v1/patients/me",
        headers=headers,
        json={"full_name": expected_full_name, "address": expected_address},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["full_name"] == expected_full_name
    assert update_response.json()["address"] == expected_address

    reloaded_response = sqlserver_client.get("/api/v1/patients/me", headers=headers)
    assert reloaded_response.status_code == 200, reloaded_response.text
    reloaded = reloaded_response.json()
    assert reloaded["full_name"] == expected_full_name
    assert reloaded["address"] == expected_address
    assert reloaded["patient_id"] == original["patient_id"]
    assert reloaded["username"] == original["username"]

    current_user_response = sqlserver_client.get("/api/v1/auth/me", headers=headers)
    assert current_user_response.status_code == 200, current_user_response.text
    assert current_user_response.json()["full_name"] == expected_full_name


def test_register_then_login_is_visible_inside_outer_transaction(
    sqlserver_client: TestClient,
) -> None:
    suffix = uuid4().hex[:16]
    username = f"it_{suffix}"
    register_response = sqlserver_client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "password": DEMO_PASSWORD,
            "confirm_password": DEMO_PASSWORD,
            "full_name": "SQL Server Integration Patient",
            "phone": "0901234567",
            "email": f"{username}@example.com",
            "date_of_birth": "2000-01-01",
            "gender": "MALE",
            "address": "Rollback-only integration address",
        },
    )
    assert register_response.status_code == 201, register_response.text
    registered = register_response.json()
    assert registered["username"] == username
    assert registered["role"] == "PATIENT"
    assert registered["user_id"] > 0
    assert registered["patient_id"] > 0

    headers = _login(sqlserver_client, username)
    current_user_response = sqlserver_client.get("/api/v1/auth/me", headers=headers)
    assert current_user_response.status_code == 200, current_user_response.text
    current_user = current_user_response.json()
    assert current_user["username"] == username
    assert current_user["patient_id"] == registered["patient_id"]

    dashboard_response = sqlserver_client.get("/api/v1/dashboard/me", headers=headers)
    assert dashboard_response.status_code == 200, dashboard_response.text
    dashboard = dashboard_response.json()
    assert dashboard["total_appointments"] == 0
    assert dashboard["total_medical_records"] == 0
    assert dashboard["total_invoices"] == 0
    assert dashboard["unpaid_invoices"] == 0
    assert dashboard["upcoming_appointment"] is None
