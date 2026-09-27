"""Regression tests for the simplified patient booking flow."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n
from frontend.views.booking_view import BookingView
from frontend.views.common import BaseApiView
from frontend.widgets.wizard_stepper import WizardStepper


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def booking_view(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[BookingView]:
    i18n = get_i18n()
    previous_language = i18n.current_language
    i18n.set_language("vi")
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    view = BookingView(MagicMock(spec=ApiClient))
    view.resize(1100, 680)
    view.show()
    qt_app.processEvents()
    yield view
    view.close()
    view.deleteLater()
    i18n.set_language(previous_language)


def test_booking_uses_one_canonical_stepper_and_unframed_canvas(
    booking_view: BookingView,
) -> None:
    steppers = booking_view.findChildren(WizardStepper)
    assert steppers == [booking_view.step_indicator]
    assert booking_view.step_indicator.steps == (
        "Chuyên khoa",
        "Bác sĩ",
        "Ngày & giờ",
        "Xác nhận",
    )
    assert booking_view.step_container.objectName() == "bookingWizardSurface"
    assert booking_view.step_container.maximumWidth() == 1280


def test_step_two_has_context_chip_segmented_mode_and_one_date_affordance(
    booking_view: BookingView,
    qt_app: QApplication,
) -> None:
    booking_view.selected_specialty = {
        "specialty_id": 5,
        "specialty_name": "Cơ Xương Khớp",
    }
    booking_view._go_to_step(1)
    qt_app.processEvents()

    assert booking_view.step2_title.text() == "Chọn bác sĩ"
    assert booking_view.step2_back_btn.objectName() == "bookingContextChip"
    assert booking_view.step2_back_btn.text() == "Cơ Xương Khớp · Thay đổi"
    assert booking_view.mode_by_date_btn.parentWidget() is booking_view.mode_segment
    assert booking_view.mode_by_doctor_btn.parentWidget() is booking_view.mode_segment
    assert booking_view.step2_date_edit.isHidden()
    assert booking_view.s2_open_cal_btn.text() == "Ngày khác…"


def test_date_selection_updates_results_without_confirmation_button(
    booking_view: BookingView,
) -> None:
    target = QDate(2026, 9, 28)
    booking_view.step2_date_edit.blockSignals(True)
    booking_view.step2_date_edit.setDate(target)
    booking_view.step2_date_edit.blockSignals(False)
    booking_view._load_doctors_for_date()

    assert booking_view.by_date_doc_header.text() == "Bác sĩ làm việc Thứ Hai, 28/09/2026"
    assert booking_view.s2_open_cal_btn.objectName() == "bookingDateChip"
