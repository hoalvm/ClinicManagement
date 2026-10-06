"""Safety and date checks that run without opening SQL Server."""

from datetime import datetime, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from backend.app.db import init_db, reset_seed
from backend.app.db.seed import build_demo_appointments, demo_live_slot, validate_demo_fixture


def test_reset_refuses_the_existing_application_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        init_db,
        "get_settings",
        lambda: SimpleNamespace(db_name="ClinicManagementDB", app_mode="normal"),
    )
    with pytest.raises(ValueError, match="only for ClinicManagementDemoDB"):
        init_db.init_database(reset=True, verbose=False)


@pytest.mark.parametrize(
    ("app_mode", "db_name"),
    [
        ("production", "ClinicManagementDB"),
        ("demo", "ClinicManagementDemoDB"),
        ("normal", "ClinicManagementDB"),
    ],
)
def test_project_seed_reset_requires_exact_demo_target(
    monkeypatch: pytest.MonkeyPatch, app_mode: str, db_name: str,
) -> None:
    monkeypatch.setattr(
        reset_seed,
        "get_settings",
        lambda: SimpleNamespace(db_name=db_name, app_mode=app_mode),
    )
    with pytest.raises(RuntimeError, match="No database was changed"):
        reset_seed.validate_reset_settings()


def test_production_schema_changes_require_explicit_dba_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        init_db,
        "get_settings",
        lambda: SimpleNamespace(db_name="ClinicManagementProdDB", app_mode="production"),
    )
    with pytest.raises(RuntimeError, match="--provision-existing"):
        init_db.init_database(verbose=False)
    with pytest.raises(RuntimeError, match="explicit DBA migration"):
        init_db.ensure_database_initialized()


def test_fixture_reserves_the_live_booking_slot_and_is_internally_valid() -> None:
    now = datetime(2026, 10, 5, 9, 59, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    rows = build_demo_appointments(now)
    live_day, live_start = demo_live_slot(now)
    validate_demo_fixture(rows, live_slot=(live_day, live_start))
    assert live_start == time(10)
    assert live_day == now.date()
    assert not any(
        doctor == "doctor01" and day == live_day
        and begins == live_start and status != "CANCELLED"
        for _, _, doctor, day, begins, status, _ in rows
    )


def test_live_clock_after_hours_does_not_seed_future_checkins() -> None:
    now = datetime(2026, 10, 6, 18, 30, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    rows = build_demo_appointments(now)
    live_day, live_start = demo_live_slot(now)
    validate_demo_fixture(rows, live_slot=(live_day, live_start))
    assert (live_day.isoformat(), live_start) == ("2026-10-07", time(8))
    assert all(
        day <= now.date()
        for _, _, _, day, _, status, _ in rows
        if status in {"CHECKED_IN", "IN_PROGRESS", "COMPLETED"}
    )


def test_weekend_clock_keeps_started_visits_in_the_past() -> None:
    now = datetime(2026, 10, 10, 10, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
    rows = build_demo_appointments(now)
    validate_demo_fixture(rows, live_slot=demo_live_slot(now))
    assert all(
        day < now.date()
        for _, _, _, day, _, status, _ in rows
        if status in {"CHECKED_IN", "IN_PROGRESS"}
    )
