"""Regressions for live i18n controls and replaceable booking reads."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.booking_view import BookingView
from frontend.views.common import BaseApiView
from frontend.widgets.pagination import PaginationWidget
from frontend.widgets.status_badge import StatusBadge, status_colors


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture()
def restore_language() -> Iterator[None]:
    i18n = get_i18n()
    previous = i18n.current_language
    yield
    i18n.set_language(previous)


def test_status_badge_retranslates_without_changing_raw_semantics(
    qt_app: QApplication,
    restore_language: None,
) -> None:
    i18n = get_i18n()
    i18n.set_language("vi")
    badge = StatusBadge("PAID")
    original_colors = status_colors(badge.status)

    assert badge.text() == "Đã thanh toán"
    assert badge.accessibleName() == "Trạng thái: Đã thanh toán"

    i18n.set_language("en")
    qt_app.processEvents()

    assert badge.text() == "Paid"
    assert badge.accessibleName() == "Status: Paid"
    assert badge.status == "PAID"
    assert badge.property("status") == "paid"
    assert status_colors(badge.status) == original_colors
    badge.deleteLater()


def test_pagination_retranslates_visible_and_accessible_text(
    qt_app: QApplication,
    restore_language: None,
) -> None:
    i18n = get_i18n()
    i18n.set_language("vi")
    pagination = PaginationWidget()
    pagination.set_page(2, 3, 25)

    assert pagination._summary.text() == t(
        "pagination_summary",
        first=11,
        last=20,
        total=25,
        page=2,
        total_pages=3,
    )
    assert pagination._previous.text() == "Trước"
    assert pagination._page_size.accessibleName() == "Số dòng mỗi trang"

    i18n.set_language("en")
    qt_app.processEvents()

    assert pagination._summary.text() == "Showing 11–20 of 25  ·  Page 2/3"
    assert pagination._rows_label.text() == "Rows"
    assert pagination._previous.text() == "Previous"
    assert pagination._next.text() == "Next"
    assert pagination._summary.accessibleName() == "Pagination summary"
    assert pagination._page_size.accessibleName() == "Rows per page"
    pagination.deleteLater()


def test_booking_date_reads_replace_older_choices(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending: list[dict[str, Any]] = []

    def capture_task(
        _view: BaseApiView,
        key: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        **kwargs: Any,
    ) -> bool:
        pending.append(
            {
                "key": key,
                "operation": operation,
                "on_success": on_success,
                **kwargs,
            }
        )
        return True

    monkeypatch.setattr(BaseApiView, "run_api_task", capture_task)
    view = BookingView(MagicMock(spec=ApiClient))
    pending.clear()  # Discard the initial specialty catalog read.

    view.selected_specialty = {"specialty_id": 7, "specialty_name": "Tim mạch"}
    view._booking_mode = "by_date"
    first_date = QDate.currentDate().addDays(1)
    second_date = first_date.addDays(1)

    view.step2_date_edit.blockSignals(True)
    view.step2_date_edit.setDate(first_date)
    view.step2_date_edit.blockSignals(False)
    view._load_doctors_for_date()
    first = pending[-1]

    view.step2_date_edit.blockSignals(True)
    view.step2_date_edit.setDate(second_date)
    view.step2_date_edit.blockSignals(False)
    view._load_doctors_for_date()
    second = pending[-1]

    assert first["key"] != second["key"]
    assert first["is_current"]() is False
    assert second["is_current"]() is True

    # Only the current response is allowed to update the choice list.
    if first["is_current"]():
        first["on_success"]([{"doctor_id": 1, "full_name": "Old"}])
    if second["is_current"]():
        second["on_success"]([{"doctor_id": 2, "full_name": "Newest"}])
    labels = [label.text() for label in view.by_date_doc_widget.findChildren(type(view.step2_title))]
    assert any("Newest" in label for label in labels)
    assert all("Old" not in label for label in labels)
    view.deleteLater()
    qt_app.processEvents()


def test_booking_slot_reads_replace_older_dates(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending: list[dict[str, Any]] = []

    def capture_task(
        _view: BaseApiView,
        key: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        **kwargs: Any,
    ) -> bool:
        pending.append(
            {
                "key": key,
                "operation": operation,
                "on_success": on_success,
                **kwargs,
            }
        )
        return True

    monkeypatch.setattr(BaseApiView, "run_api_task", capture_task)
    view = BookingView(MagicMock(spec=ApiClient))
    pending.clear()
    view.selected_doctor = {"doctor_id": 9, "full_name": "Bác sĩ A"}

    first_date = QDate.currentDate().addDays(1)
    second_date = first_date.addDays(1)
    view.slot_date_edit.blockSignals(True)
    view.slot_date_edit.setDate(first_date)
    view.slot_date_edit.blockSignals(False)
    view._load_available_slots()
    first = pending[-1]

    view.slot_date_edit.blockSignals(True)
    view.slot_date_edit.setDate(second_date)
    view.slot_date_edit.blockSignals(False)
    view._load_available_slots()
    second = pending[-1]

    assert first["key"] != second["key"]
    assert first["is_current"]() is False
    assert second["is_current"]() is True

    latest_result = {
        "has_schedule": True,
        "slots": [
            {
                "start_time": "10:00",
                "end_time": "10:30",
                "is_available": True,
            }
        ],
    }
    if second["is_current"]():
        second["on_success"](latest_result)
    assert [button.text() for button in view._slot_widgets] == ["10:00–10:30"]

    # Moving back to the old date would create a new request; the old response
    # cannot become current merely because it completes later.
    assert first["is_current"]() is False
    view.deleteLater()
    qt_app.processEvents()


def test_reception_dashboard_uses_responsive_page(qt_app: QApplication) -> None:
    from frontend.views.reception_dashboard_view import ReceptionDashboardView
    from frontend.widgets.responsive_page import ResponsivePage

    view = ReceptionDashboardView(MagicMock(spec=ApiClient))
    page = view.findChild(ResponsivePage)

    assert page is view.responsive_page
    assert page.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    assert page.widgetResizable()
    view.deleteLater()
    qt_app.processEvents()
