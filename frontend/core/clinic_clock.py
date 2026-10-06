"""The server's clinic clock shared by every desktop date selector.

The application can use sample records with either a fixed demonstration clock
or the real clinic clock. Live time advances from the last server reading.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from threading import RLock
from time import monotonic
from typing import Any

from PySide6.QtCore import QDate


class ClinicClock:
    def __init__(self) -> None:
        self._lock = RLock()
        self._snapshot: datetime | None = None
        self._read_at = 0.0
        self._demo_mode = False
        self._clock_fixed = False
        self._timezone = "Asia/Ho_Chi_Minh"

    def set_from_payload(self, payload: dict[str, Any]) -> None:
        value = payload.get("clinic_now")
        if not isinstance(value, str):
            raise ValueError("Server không cung cấp thời gian phòng khám hợp lệ.")
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Server không cung cấp thời gian phòng khám hợp lệ.") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("Thời gian phòng khám phải có múi giờ.")
        timezone = payload.get("timezone")
        demo_mode = payload.get("demo_mode")
        if not isinstance(timezone, str) or not timezone or not isinstance(demo_mode, bool):
            raise ValueError("Server không cung cấp cấu hình đồng hồ phòng khám hợp lệ.")
        clock_fixed = payload.get("clock_fixed", demo_mode)
        if not isinstance(clock_fixed, bool) or (clock_fixed and not demo_mode):
            raise ValueError("Server không cung cấp cấu hình đồng hồ phòng khám hợp lệ.")
        with self._lock:
            self._snapshot = parsed
            self._read_at = monotonic()
            self._demo_mode = demo_mode
            self._clock_fixed = clock_fixed
            self._timezone = timezone

    def clear(self) -> None:
        with self._lock:
            self._snapshot = None
            self._demo_mode = False
            self._clock_fixed = False

    def now(self) -> datetime:
        with self._lock:
            if self._snapshot is None:
                return datetime.now().astimezone()
            if self._clock_fixed:
                return self._snapshot
            return self._snapshot + timedelta(seconds=monotonic() - self._read_at)

    def today(self) -> date:
        return self.now().date()

    def today_qdate(self) -> QDate:
        current = self.today()
        return QDate(current.year, current.month, current.day)

    @property
    def demo_mode(self) -> bool:
        with self._lock:
            return self._demo_mode

    def display_label(self) -> str:
        with self._lock:
            if self._snapshot is None or not self._demo_mode:
                return ""
            clock_fixed = self._clock_fixed
            timezone = self._timezone
        label = "Giờ mô phỏng" if clock_fixed else "Giờ phòng khám"
        return f"DỮ LIỆU MẪU · {label}: {self.now():%d/%m/%Y %H:%M} ({timezone})"


clinic_clock = ClinicClock()


def clinic_today_qdate() -> QDate:
    return clinic_clock.today_qdate()
