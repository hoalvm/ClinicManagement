"""Price catalog management keeps production invoice prices under admin control."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.api.routes import catalog
from backend.app.core.exceptions import AuthorizationError, ConflictError, ValidationError
from backend.app.models import ChargeCatalog
from backend.app.schemas.reception import ChargeCatalogCreate


@pytest.fixture(autouse=True)
def fixed_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(catalog, "clinic_naive_now", lambda: datetime(2026, 10, 6, 8, 0))
    monkeypatch.setattr(catalog, "record_audit_event", lambda *_args, **_kwargs: None)


def _body(*, code: str = "CONS-GEN-001", price: str = "175000.00") -> ChargeCatalogCreate:
    return ChargeCatalogCreate(
        code=code,
        display_name="Khám Nội tổng quát",
        category="CONSULTATION",
        specialty_id=3,
        unit_price=Decimal(price),
    )


def test_only_admin_can_create_catalog_charge() -> None:
    session = MagicMock()
    staff = SimpleNamespace(user_id=7, role="STAFF")
    with pytest.raises(AuthorizationError):
        catalog.create_charge(_body(), session, staff)
    session.add.assert_not_called()


def test_production_rejects_medication_price_without_dispensing_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    session = MagicMock()
    medication = ChargeCatalogCreate(
        code="MED-AMOX-001",
        display_name="Amoxicillin 500 mg",
        category="MEDICATION",
        specialty_id=None,
        unit_price=Decimal("25000.00"),
    )
    with pytest.raises(ValidationError) as exc:
        catalog.create_charge(medication, session, SimpleNamespace(user_id=1, role="ADMIN"))
    assert exc.value.status_code == 422
    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_creating_consultation_price_retires_old_version_atomically() -> None:
    session = MagicMock()
    session.scalar.return_value = None
    session.get.return_value = SimpleNamespace(is_active=True)
    old = ChargeCatalog(
        code="CONS-GEN-001",
        display_name="Khám Nội tổng quát",
        category="CONSULTATION",
        specialty_id=3,
        unit_price=Decimal("150000.00"),
        is_active=True,
        effective_from=datetime(2026, 1, 1),
    )
    old.charge_id = 10
    session.scalars.return_value.all.return_value = [old]

    def add_new(row: ChargeCatalog) -> None:
        row.charge_id = 11

    session.add.side_effect = add_new
    admin = SimpleNamespace(user_id=1, role="ADMIN")
    result = catalog.create_charge(_body(code="CONS-GEN-002", price="175000.00"), session, admin)

    assert old.is_active is False
    assert old.effective_to == datetime(2026, 10, 6, 8, 0)
    assert session.flush.call_count == 2
    assert result.charge_id == 11
    assert result.unit_price == Decimal("175000.00")
    session.commit.assert_called_once_with()


def test_production_price_change_refused_while_future_visit_is_booked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    session = MagicMock()
    # The price code is new, but a future active appointment already exists.
    session.scalar.side_effect = [None, 42]
    session.get.return_value = SimpleNamespace(is_active=True)

    with pytest.raises(ConflictError, match="lịch hẹn tương lai"):
        catalog.create_charge(
            _body(code="CONS-GEN-002"),
            session,
            SimpleNamespace(user_id=1, role="ADMIN"),
        )

    session.add.assert_not_called()
    session.commit.assert_not_called()


def test_production_price_change_allowed_without_future_visit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(catalog, "get_settings", lambda: SimpleNamespace(app_mode="production"))
    session = MagicMock()
    session.scalar.side_effect = [None, None]
    session.get.return_value = SimpleNamespace(is_active=True)
    session.scalars.return_value.all.return_value = []

    def add_new(row: ChargeCatalog) -> None:
        row.charge_id = 11

    session.add.side_effect = add_new
    result = catalog.create_charge(
        _body(code="CONS-GEN-002"),
        session,
        SimpleNamespace(user_id=1, role="ADMIN"),
    )
    assert result.charge_id == 11
    session.commit.assert_called_once_with()


def test_last_consultation_price_cannot_be_retired_for_active_specialty() -> None:
    session = MagicMock()
    charge = ChargeCatalog(
        code="CONS-GEN-001",
        display_name="Khám Nội tổng quát",
        category="CONSULTATION",
        specialty_id=3,
        unit_price=Decimal("175000.00"),
        is_active=True,
        effective_from=datetime(2026, 1, 1),
    )
    charge.charge_id = 10
    session.get.side_effect = [charge, SimpleNamespace(is_active=True)]

    with pytest.raises(ConflictError):
        catalog.retire_charge(10, session, SimpleNamespace(user_id=1, role="ADMIN"))
    session.commit.assert_not_called()
