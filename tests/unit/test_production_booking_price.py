"""Production must never create a visit that cannot be priced at service time."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from backend.app.core.exceptions import ConflictError
from backend.app.services.booking_service import BookingService


def _production_service(monkeypatch: pytest.MonkeyPatch) -> tuple[BookingService, MagicMock]:
    monkeypatch.setattr(
        "backend.app.services.booking_service.get_settings",
        lambda: SimpleNamespace(app_mode="production"),
    )
    monkeypatch.setattr(
        "backend.app.services.booking_service.clinic_now",
        lambda: datetime(2026, 10, 5, 7, 0),
    )
    session = MagicMock()
    session.get.return_value = SimpleNamespace(patient_id=3)
    doctor = SimpleNamespace(
        doctor_id=4,
        specialty_id=5,
        user=SimpleNamespace(is_active=True, role="DOCTOR", full_name="Bác sĩ An"),
        specialty=SimpleNamespace(is_active=True, specialty_name="Nội tổng quát"),
        clinic=SimpleNamespace(is_active=True, clinic_name="Cơ sở A"),
    )
    service = BookingService(session)
    service._lock_booking_resources = MagicMock()
    service.doctor_repo.get_doctor_by_id = MagicMock(return_value=doctor)
    service.doctor_repo.get_schedules = MagicMock(
        return_value=[
            SimpleNamespace(
                is_active=True,
                start_time=time(8, 0),
                end_time=time(10, 0),
                slot_duration=30,
            )
        ]
    )
    service._schedule_exceptions = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_doctor = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient = MagicMock(return_value=[])
    service.appointment_repo.get_active_appointments_for_patient_all = MagicMock(return_value=[])
    return service, session


def test_missing_fee_blocks_booking_and_marks_slots_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _production_service(monkeypatch)
    session.scalars.return_value.all.return_value = []
    with pytest.raises(ConflictError, match="phí khám"):
        service.validate_target_slot(3, 4, date(2026, 10, 5), time(8), time(8, 30))
    slots = service.get_available_slots(4, date(2026, 10, 5), patient_id=3)
    assert slots.has_schedule
    assert slots.slots
    assert all(not slot.is_available for slot in slots.slots)
    assert "phí khám" in str(slots.slots[0].reason)


def test_fee_must_be_effective_at_appointment_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service, session = _production_service(monkeypatch)
    fee = SimpleNamespace(
        effective_from=datetime(2026, 10, 5, 9, 0),
        effective_to=None,
        unit_price=Decimal("150000.00"),
    )
    session.scalars.return_value.all.return_value = [fee]
    with pytest.raises(ConflictError, match="phí khám"):
        service.validate_target_slot(3, 4, date(2026, 10, 5), time(8), time(8, 30))
    assert service.validate_target_slot(
        3, 4, date(2026, 10, 5), time(9), time(9, 30)
    ) is service.doctor_repo.get_doctor_by_id.return_value


def test_booking_serializes_with_price_change(monkeypatch: pytest.MonkeyPatch) -> None:
    service, session = _production_service(monkeypatch)
    service._lock_specialty_pricing = MagicMock()
    session.scalars.return_value.all.return_value = [
        SimpleNamespace(
            effective_from=datetime(2026, 10, 5, 7, 0),
            effective_to=None,
            unit_price=Decimal("150000.00"),
        )
    ]
    service.validate_target_slot(3, 4, date(2026, 10, 5), time(8), time(8, 30))
    service._lock_specialty_pricing.assert_called_once_with(5)
