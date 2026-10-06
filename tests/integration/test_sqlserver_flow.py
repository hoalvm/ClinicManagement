"""Opt-in API checks against the seeded persistent project SQL Server database.

Run with ``RUN_SQLSERVER_INTEGRATION=1 pytest -q tests/integration``. Every
request gets a real SQLAlchemy session bound to one connection.  Application
``commit()`` calls only release a savepoint; the outer transaction is rolled
back after each test so no test records remain in the project database.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from threading import Event
from time import sleep
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.clock import clinic_now, clinic_today
from backend.app.db.seed import SEED_VERSION, demo_live_slot
from backend.app.db.session import SessionLocal, engine, get_db
from backend.app.main import app
from backend.app.models import Appointment, Doctor, Patient, User
from backend.app.services.booking_service import BookingService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_SQLSERVER_INTEGRATION", "").strip() != "1",
        reason="set RUN_SQLSERVER_INTEGRATION=1 to use the configured SQL Server",
    ),
]

DEMO_PASSWORD = "Password123!"
PROJECT_DB_NAME = "ClinicManagementDB"


def _next_workday(start: date, offset: int = 1) -> date:
    day = start
    for _ in range(offset):
        day += timedelta(days=1)
        while day.isoweekday() > 5:
            day += timedelta(days=1)
    return day


@pytest.fixture
def sqlserver_client() -> Generator[TestClient, None, None]:
    """Serve the real app while containing writes in a rollback-only transaction."""

    connection = engine.connect()
    if connection.dialect.name != "mssql" or connection.dialect.driver != "pyodbc":
        connection.close()
        pytest.fail("Integration tests require Microsoft SQL Server through pyodbc")

    outer_transaction = connection.begin()
    database_name = connection.exec_driver_sql("SELECT DB_NAME()").scalar_one()
    if database_name != PROJECT_DB_NAME:
        outer_transaction.rollback()
        connection.close()
        pytest.fail(f"Integration tests require {PROJECT_DB_NAME}")
    marker = connection.exec_driver_sql(
        "SELECT COUNT(*) FROM dbo.SchemaMigrations WHERE MigrationID = ?",
        (SEED_VERSION,),
    ).scalar_one()
    if marker != 1:
        outer_transaction.rollback()
        connection.close()
        pytest.fail("Integration tests require the project synthetic seed")

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


def _login(
    client: TestClient, username: str, password: str = DEMO_PASSWORD,
    *, legacy: bool = False,
) -> dict[str, str]:
    response = (
        client.post("/auth/login", data={"username": username, "password": password})
        if legacy
        else client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
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
    eligible_upcoming = [
        item
        for item in appointment_items
        if item["status"] in {"PENDING", "CONFIRMED"}
        and item["appointment_date"] >= clinic_today().isoformat()
    ]
    if eligible_upcoming:
        assert upcoming is not None
        assert upcoming["status"] in {"PENDING", "CONFIRMED"}
    else:
        assert upcoming is None

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
    assert paid_detail["payment"]["payment_method"] in {"CASH", "CARD", "TRANSFER"}
    assert Decimal(paid_detail["payment"]["amount"]) == Decimal(paid_detail["total_amount"])

    unpaid_invoices = _get_page(
        sqlserver_client,
        "/api/v1/invoices/me",
        headers,
        status="UNPAID",
    )
    unpaid_items = unpaid_invoices["items"]
    assert isinstance(unpaid_items, list)
    if unpaid_items:
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
    username = f"it{suffix}"
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


def test_four_role_demo_workflow_reaches_paid_invoice(
    sqlserver_client: TestClient,
) -> None:
    """Exercise the presentation path on one database and roll it all back."""

    client = sqlserver_client
    admin = _login(client, "admin", "Admin123!", legacy=True)
    patient = _login(client, "patient01")
    staff = _login(client, "reception01", "Staff123!", legacy=True)
    doctor = _login(client, "doctor01", "Doctor123!", legacy=True)
    other_doctor = _login(client, "doctor02", "Doctor123!", legacy=True)

    for credentials, expected_role in (
        (admin, "ADMIN"), (patient, "PATIENT"),
        (staff, "STAFF"), (doctor, "DOCTOR"),
    ):
        desktop_me = client.get("/auth/me", headers=credentials)
        assert desktop_me.status_code == 200, desktop_me.text
        assert desktop_me.json()["role"] == expected_role
        assert desktop_me.json()["is_active"] is True

    clock_response = client.get("/api/v1/system/time")
    assert clock_response.status_code == 200, clock_response.text
    clinic_time = datetime.fromisoformat(clock_response.json()["clinic_now"])
    assert clinic_time.date() == clinic_today()
    assert clock_response.json()["demo_mode"] is True
    assert clock_response.json()["project_database"] == PROJECT_DB_NAME
    live_day, live_start = demo_live_slot(clinic_time)
    if live_day != clinic_time.date():
        pytest.skip("Same-day check-in walkthrough needs a clinic-hours demo clock")
    live_end = (datetime.combine(live_day, live_start) + timedelta(minutes=30)).time()

    stats_response = client.get("/api/v1/admin/stats", headers=admin)
    assert stats_response.status_code == 200, stats_response.text
    initial_stats = stats_response.json()
    assert set(initial_stats) == {
        "total_appointments", "completed_appointments", "paid_revenue",
        "today_appointments", "today_completed", "today_collected", "unpaid_total",
    }
    assert client.get("/api/v1/admin/stats", headers=staff).status_code == 403

    doctor_profile_response = client.get("/api/v1/doctor/profile", headers=doctor)
    assert doctor_profile_response.status_code == 200, doctor_profile_response.text
    doctor_id = doctor_profile_response.json()["doctor_id"]
    assert doctor_profile_response.json()["doctor_name"] == "Lý Võ Mỹ Hoa"

    booked_response = client.post(
        "/api/v1/appointments",
        headers=patient,
        json={
            "doctor_id": doctor_id,
            "appointment_date": live_day.isoformat(),
            "start_time": live_start.isoformat(),
            "end_time": live_end.isoformat(),
            "reason": "Đau họng 2 ngày, ho khan",
        },
    )
    assert booked_response.status_code == 201, booked_response.text
    appointment = booked_response.json()
    appointment_id = appointment["appointment_id"]
    assert appointment["status"] == "PENDING"

    invoice_request = {
        "appointment_id": appointment_id,
        "items": [
            {"item_name": "Phí khám Nội tổng quát", "quantity": 1, "unit_price": "200000.00"},
            {"item_name": "Natri clorid 0,9% súc họng", "quantity": 1, "unit_price": "25000.00"},
        ],
    }
    early_invoice = client.post("/api/v1/reception/invoices", headers=staff, json=invoice_request)
    assert early_invoice.status_code == 409, early_invoice.text
    early_check_in = client.post(
        f"/api/v1/reception/appointments/{appointment_id}/check-in", headers=staff
    )
    assert early_check_in.status_code == 409, early_check_in.text

    confirm = client.post(
        f"/api/v1/reception/appointments/{appointment_id}/confirm", headers=staff
    )
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "CONFIRMED"
    check_in = client.post(
        f"/api/v1/reception/appointments/{appointment_id}/check-in",
        headers=staff,
        json={"notes": "Bệnh nhân đã đến quầy"},
    )
    assert check_in.status_code == 200, check_in.text
    assert check_in.json()["status"] == "CHECKED_IN"
    assert check_in.json()["queue_number"].startswith("A-")
    assert check_in.json()["check_in_at"] is not None
    assert check_in.json()["reason"] == "Đau họng 2 ngày, ho khan"

    queue = client.get("/api/v1/doctor/schedule", headers=doctor)
    assert queue.status_code == 200, queue.text
    assert any(row["AppointmentID"] == appointment_id for row in queue.json())
    other_accept = client.put(
        f"/api/v1/doctor/appointments/{appointment_id}/accept", headers=other_doctor
    )
    assert other_accept.status_code == 403, other_accept.text
    admin_accept = client.put(
        f"/api/v1/doctor/appointments/{appointment_id}/accept", headers=admin
    )
    assert admin_accept.status_code == 403, admin_accept.text

    accept = client.put(f"/api/v1/doctor/appointments/{appointment_id}/accept", headers=doctor)
    assert accept.status_code == 200, accept.text
    complete = client.post(
        f"/api/v1/doctor/appointments/{appointment_id}/complete",
        headers=doctor,
        json={
            "symptoms": "Đau họng 2 ngày, ho khan, không khó thở",
            "diagnosis": "Viêm họng cấp (J02.9), theo dõi",
            "notes": "Súc họng, uống đủ nước; tái khám nếu triệu chứng tăng.",
            "prescription_items": [{
                "medicine_name": "Natri clorid 0,9% súc họng",
                "quantity": 1,
                "dosage": "1 chai",
                "instructions": "Súc họng theo hướng dẫn trên nhãn.",
            }],
        },
    )
    assert complete.status_code == 200, complete.text

    completed_appointment = client.get(
        f"/api/v1/appointments/me/{appointment_id}", headers=patient
    )
    assert completed_appointment.status_code == 200, completed_appointment.text
    assert completed_appointment.json()["status"] == "COMPLETED"
    record_id = completed_appointment.json()["medical_record_id"]
    assert record_id is not None
    record = client.get(f"/api/v1/medical-records/me/{record_id}", headers=patient)
    assert record.status_code == 200, record.text
    assert record.json()["prescription"]["items"][0]["medicine_name"] == (
        "Natri clorid 0,9% súc họng"
    )

    created_invoice = client.post(
        "/api/v1/reception/invoices", headers=staff, json=invoice_request
    )
    assert created_invoice.status_code == 200, created_invoice.text
    invoice = created_invoice.json()
    invoice_id = invoice["invoice_id"]
    assert invoice["status"] == "UNPAID"
    assert Decimal(invoice["total_amount"]) == Decimal("225000.00")
    assert client.post(
        "/api/v1/reception/invoices", headers=staff, json=invoice_request
    ).status_code == 409
    assert client.post(
        f"/api/v1/reception/invoices/{invoice_id}/pay",
        headers=staff,
        json={"payment_method": "TRANSFER", "amount": "224999.00"},
    ).status_code == 422

    paid = client.post(
        f"/api/v1/reception/invoices/{invoice_id}/pay",
        headers=staff,
        json={"payment_method": "TRANSFER", "amount": "225000.00"},
    )
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "PAID"
    assert paid.json()["payment_method"] == "TRANSFER"
    assert Decimal(paid.json()["change_due"]) == Decimal("0.00")
    assert client.post(
        f"/api/v1/reception/invoices/{invoice_id}/pay",
        headers=staff,
        json={"payment_method": "TRANSFER", "amount": "225000.00"},
    ).status_code == 409

    patient_invoice = client.get(f"/api/v1/invoices/me/{invoice_id}", headers=patient)
    assert patient_invoice.status_code == 200, patient_invoice.text
    assert patient_invoice.json()["payment"]["payment_method"] == "TRANSFER"
    final_stats = client.get("/api/v1/admin/stats", headers=admin)
    assert final_stats.status_code == 200, final_stats.text
    assert final_stats.json()["total_appointments"] == initial_stats["total_appointments"] + 1
    assert final_stats.json()["completed_appointments"] == initial_stats["completed_appointments"] + 1
    assert Decimal(final_stats.json()["paid_revenue"]) == (
        Decimal(initial_stats["paid_revenue"]) + Decimal("225000.00")
    )


def test_demo_secondary_workflows_and_inactive_patient_guard(
    sqlserver_client: TestClient,
) -> None:
    client = sqlserver_client
    admin = _login(client, "admin", "Admin123!", legacy=True)
    staff = _login(client, "reception01", "Staff123!", legacy=True)
    patient01 = _login(client, "patient01")
    patient02 = _login(client, "patient02")
    doctor01 = _login(client, "doctor01", "Doctor123!", legacy=True)
    doctor02 = _login(client, "doctor02", "Doctor123!", legacy=True)
    doctor03 = _login(client, "doctor03", "Doctor123!", legacy=True)
    doctor_ids = {
        name: client.get("/api/v1/doctor/profile", headers=credentials).json()["doctor_id"]
        for name, credentials in (
            ("doctor01", doctor01), ("doctor02", doctor02), ("doctor03", doctor03)
        )
    }
    live_day, _ = demo_live_slot(clinic_now())
    visit_day = _next_workday(live_day, 3).isoformat()
    reschedule_day = _next_workday(live_day, 4).isoformat()

    first = client.post(
        "/api/v1/appointments", headers=patient01,
        json={"doctor_id": doctor_ids["doctor01"], "appointment_date": visit_day,
              "start_time": "14:00:00", "end_time": "14:30:00", "reason": "Ho khan"},
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/api/v1/appointments", headers=patient01,
        json={"doctor_id": doctor_ids["doctor03"], "appointment_date": visit_day,
              "start_time": "14:30:00", "end_time": "15:00:00", "reason": "Kiểm tra tim mạch"},
    )
    assert second.status_code == 201, second.text
    assert first.json()["clinic"]["clinic_id"] == second.json()["clinic"]["clinic_id"]
    same_specialty = client.post(
        "/api/v1/appointments", headers=patient01,
        json={"doctor_id": doctor_ids["doctor01"], "appointment_date": visit_day,
              "start_time": "15:00:00", "end_time": "15:30:00", "reason": "Khám lại"},
    )
    assert same_specialty.status_code == 409, same_specialty.text

    own_future = _get_page(client, "/api/v1/appointments/me", patient01)["items"]
    derm_future = next(
        item for item in own_future
        if item["status"] == "CONFIRMED"
        and item["doctor"]["doctor_id"] == doctor_ids["doctor02"]
        and item["appointment_date"] >= clinic_today().isoformat()
    )
    rescheduled = client.post(
        f"/api/v1/appointments/{derm_future['appointment_id']}/reschedule",
        headers=patient01,
        json={"new_appointment_date": reschedule_day, "new_start_time": "10:00:00",
              "new_end_time": "10:30:00", "reason": "Đổi ngày vì công việc"},
    )
    assert rescheduled.status_code == 200, rescheduled.text
    assert rescheduled.json()["status"] == "PENDING"
    patient02_items = _get_page(client, "/api/v1/appointments/me", patient02)["items"]
    cancellable = next(
        item for item in patient02_items
        if item["status"] == "PENDING"
        and item["appointment_date"] >= clinic_today().isoformat()
    )
    cancelled = client.post(
        f"/api/v1/appointments/{cancellable['appointment_id']}/cancel",
        headers=patient02, json={"cancellation_reason": "Không thể đến khám"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"

    walk_in = client.post(
        "/api/v1/reception/appointments/book", headers=staff,
        json={
            "full_name": "Nguyễn Thị Minh Châu", "phone": "0901234578",
            "date_of_birth": "1994-03-21", "gender": "FEMALE",
            "address": "Quận Gò Vấp, TP. Hồ Chí Minh",
            "doctor_id": doctor_ids["doctor02"], "appointment_date": visit_day,
            "start_time": "16:00:00", "end_time": "16:30:00",
            "reason": "Mẩn ngứa sau dùng xà phòng", "auto_confirm": True,
        },
    )
    assert walk_in.status_code == 200, walk_in.text
    assert walk_in.json()["status"] == "CONFIRMED"
    walk_in_patient = walk_in.json()["patient"]
    users = client.get("/users/", headers=admin)
    assert users.status_code == 200, users.text
    walk_in_account = next(
        user for user in users.json() if user["UserID"] == walk_in_patient["user_id"]
    )
    assert walk_in_account["IsActive"] is False
    walk_in_rescheduled = client.post(
        f"/api/v1/reception/appointments/{walk_in.json()['appointment_id']}/reschedule",
        headers=staff,
        json={"appointment_date": reschedule_day, "start_time": "16:00:00",
              "end_time": "16:30:00", "reason": "Khách yêu cầu đổi ngày"},
    )
    assert walk_in_rescheduled.status_code == 200, walk_in_rescheduled.text
    assert walk_in_rescheduled.json()["status"] == "CONFIRMED"

    suffix = uuid4().hex[:12]
    registration = client.post(
        "/api/v1/auth/register",
        json={"username": f"locked{suffix}", "password": DEMO_PASSWORD,
              "confirm_password": DEMO_PASSWORD, "full_name": "Người bệnh khóa thử nghiệm",
              "phone": "0904567890"},
    )
    assert registration.status_code == 201, registration.text
    locked = registration.json()
    old_token = _login(client, locked["username"])
    deactivated = client.put(
        f"/users/{locked['user_id']}", headers=admin, json={"IsActive": False}
    )
    assert deactivated.status_code == 200, deactivated.text
    assert client.get("/auth/me", headers=old_token).status_code == 401
    assert client.get("/api/v1/dashboard/me", headers=old_token).status_code == 401
    refused = client.post(
        "/api/v1/reception/appointments/book", headers=staff,
        json={"patient_id": locked["patient_id"], "doctor_id": doctor_ids["doctor01"],
              "appointment_date": reschedule_day, "start_time": "16:00:00",
              "end_time": "16:30:00", "reason": "Khám thử"},
    )
    assert refused.status_code == 422, refused.text


def test_admin_catalog_lock_and_new_specialty_on_sql_server(
    sqlserver_client: TestClient,
) -> None:
    client = sqlserver_client
    admin = _login(client, "admin", "Admin123!", legacy=True)
    name = f"Chuyên khoa thử nghiệm {uuid4().hex[:10]}"
    created = client.post(
        "/specialties/", headers=admin,
        json={"SpecialtyName": name, "Description": "Chỉ dùng trong giao dịch test"},
    )
    assert created.status_code == 200, created.text
    specialty_id = created.json()["SpecialtyID"]
    assert created.json()["IsActive"] is True
    duplicate = client.post(
        "/specialties/", headers=admin,
        json={"SpecialtyName": name, "Description": "Trùng tên"},
    )
    assert duplicate.status_code == 409, duplicate.text
    removed = client.delete(f"/specialties/{specialty_id}", headers=admin)
    assert removed.status_code == 200, removed.text
    specialties = client.get("/specialties/", headers=admin)
    assert specialties.status_code == 200, specialties.text
    item = next(row for row in specialties.json() if row["SpecialtyID"] == specialty_id)
    assert item["IsActive"] is False


def test_two_concurrent_requests_cannot_claim_same_sql_server_slot() -> None:
    """A held booking serializes a second booking; both outer transactions roll back."""

    with engine.connect() as connection:
        if connection.dialect.name != "mssql" or connection.exec_driver_sql(
            "SELECT DB_NAME()"
        ).scalar_one() != PROJECT_DB_NAME:
            pytest.fail(f"Concurrency test requires {PROJECT_DB_NAME}")
    with SessionLocal() as session:
        patient_id = session.scalar(
            select(Patient.patient_id).join(User).where(User.username == "patient01")
        )
        doctor_id = session.scalar(
            select(Doctor.doctor_id).join(User).where(User.username == "doctor01")
        )
    assert patient_id is not None and doctor_id is not None
    booking_day = _next_workday(demo_live_slot(clinic_now())[0], 10)
    first_saved = Event()
    release_first = Event()
    second_started = Event()

    def book_with_rollback(*, hold_lock: bool) -> int:
        if not hold_lock:
            assert first_saved.wait(15), "First booking did not reach SQL Server"
            second_started.set()
        with engine.connect() as connection:
            outer = connection.begin()
            try:
                with Session(
                    bind=connection,
                    autoflush=False,
                    expire_on_commit=False,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    appointment = BookingService(session).create_appointment_for_patient(
                        patient_id, doctor_id, booking_day,
                        time(15), time(15, 30), "Kiểm tra đặt lịch đồng thời",
                    )
                    if hold_lock:
                        first_saved.set()
                        assert release_first.wait(15), "First transaction was not released"
                    return appointment.appointment_id
            finally:
                if outer.is_active:
                    outer.rollback()

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(book_with_rollback, hold_lock=True)
            second = pool.submit(book_with_rollback, hold_lock=False)
            try:
                assert first_saved.wait(15)
                assert second_started.wait(15)
                sleep(0.25)
                assert not second.done(), "Second booking bypassed the first transaction's lock"
            finally:
                release_first.set()
            assert first.result(timeout=15) > 0
            assert second.result(timeout=15) > 0
    finally:
        release_first.set()
    with SessionLocal() as session:
        assert session.scalar(
            select(Appointment.appointment_id).where(
                Appointment.patient_id == patient_id,
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == booking_day,
                Appointment.start_time == time(15),
                Appointment.reason == "Kiểm tra đặt lịch đồng thời",
            )
        ) is None
