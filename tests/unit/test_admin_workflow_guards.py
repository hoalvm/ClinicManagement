"""Guard and statistics regressions for the admin demo workflow."""

from datetime import date, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.app.api.routes.admin import get_admin_stats, load_admin_stats
from backend.app.core.exceptions import AuthorizationError
from backend.app.routers._admin_guards import flush_or_error, require_appointments_covered
from backend.app.routers.statistics import overview
from backend.app.routers.users import update_user
from backend.app.schemas import ScheduleCreate, UserCreate, UserUpdate


def test_schedule_cannot_be_removed_with_unfinished_booking() -> None:
    appt = SimpleNamespace(
        appointment_date=date(2026, 10, 5),
        start_time=time(9),
        end_time=time(9, 30),
    )
    shift = SimpleNamespace(
        schedule_id=7,
        day_of_week=1,
        start_time=time(8),
        end_time=time(12),
        slot_duration=30,
        is_active=True,
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.side_effect = [[appt], [shift]]
    with pytest.raises(HTTPException) as exc:
        require_appointments_covered(db, doctor_id=5, excluded_schedule_id=7)
    assert exc.value.status_code == 409


def test_admin_stats_revenue_uses_recorded_payments() -> None:
    db = MagicMock()
    db.scalar.side_effect = [12, 5, 4, 1, Decimal("250000.00"), Decimal("100000.00"), Decimal("50000.00")]
    stats = load_admin_stats(db, date(2026, 10, 5))
    assert stats.total_appointments == 12
    assert stats.completed_appointments == 5
    assert stats.today_appointments == 4
    assert stats.today_completed == 1
    assert stats.paid_revenue == Decimal("250000.00")
    assert stats.today_collected == Decimal("100000.00")
    assert stats.unpaid_total == Decimal("50000.00")


def test_admin_stats_rejects_non_admin() -> None:
    with pytest.raises(AuthorizationError):
        get_admin_stats(MagicMock(), SimpleNamespace(role="STAFF"))


def test_legacy_admin_overview_includes_live_operational_totals() -> None:
    db = MagicMock()
    db.query.return_value.scalar.return_value = 0
    db.query.return_value.filter.return_value.scalar.return_value = 0
    db.query.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = []
    db.scalar.side_effect = [12, 5, 4, 1, Decimal("250000"), Decimal("100000"), Decimal("50000")]
    result = overview(db, admin=SimpleNamespace(role="ADMIN"))
    assert result["total_appointments"] == 12
    assert result["completed_appointments"] == 5
    assert result["paid_revenue"] == 250000.0


def test_admin_input_validation_rejects_blank_and_invalid_shift() -> None:
    with pytest.raises(ValueError):
        UserCreate(
            Username=" ", Password="Password123!", FullName="Test", Role="STAFF"
        )
    with pytest.raises(ValueError):
        ScheduleCreate(
            DoctorID=1,
            DayOfWeek=1,
            StartTime=time(8),
            EndTime=time(9, 10),
            SlotDuration=30,
        )


def test_admin_flush_hides_database_constraint_details() -> None:
    db = MagicMock()
    db.flush.side_effect = IntegrityError("INSERT INTO Users secret", {}, Exception("private SQL"))
    with pytest.raises(HTTPException) as exc:
        flush_or_error(db)
    assert exc.value.status_code == 409
    assert "private SQL" not in exc.value.detail
    db.rollback.assert_called_once_with()


def test_admin_cannot_disable_patient_with_open_booking() -> None:
    db = MagicMock()
    user = SimpleNamespace(
        user_id=7,
        username="patient07",
        role="PATIENT",
        is_active=True,
        doctor=None,
        patient=SimpleNamespace(patient_id=21),
    )
    db.query.return_value.filter.return_value.first.return_value = user
    db.query.return_value.filter.return_value.filter.return_value.count.return_value = 1
    with pytest.raises(HTTPException) as exc:
        update_user(7, UserUpdate(IsActive=False), db, SimpleNamespace(user_id=1, role="ADMIN"))
    assert exc.value.status_code == 409
    db.commit.assert_not_called()
