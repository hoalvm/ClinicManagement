"""Production slot closures must block only the affected times."""

from datetime import date, time
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.routers.schedules import ScheduleExceptionCreate
from backend.app.services.booking_service import BookingService


def test_partial_closure_blocks_overlapping_slot_only() -> None:
    leave = SimpleNamespace(start_time=time(10, 0), end_time=time(11, 0))
    assert BookingService._blocked_by_exception(time(10, 30), time(11, 0), [leave])
    assert not BookingService._blocked_by_exception(time(9, 30), time(10, 0), [leave])
    assert not BookingService._blocked_by_exception(time(11, 0), time(11, 30), [leave])


def test_full_day_closure_blocks_every_slot() -> None:
    leave = SimpleNamespace(start_time=None, end_time=None)
    assert BookingService._blocked_by_exception(time(8, 0), time(8, 30), [leave])


@pytest.mark.parametrize(
    ("start", "end"),
    [(time(11), time(10)), (time(10), None), (None, time(11))],
)
def test_closure_rejects_invalid_intervals(start: time | None, end: time | None) -> None:
    with pytest.raises(ValidationError):
        ScheduleExceptionCreate(
            doctor_id=1,
            exception_date=date(2026, 10, 7),
            start_time=start,
            end_time=end,
            reason="Bác sĩ nghỉ phép",
        )
