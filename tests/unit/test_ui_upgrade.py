"""Regression coverage for the responsive PySide UI upgrade."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QApplication, QFrame, QPushButton, QWidget

from frontend.api.api_client import ApiClient
from frontend.core.session import SessionState
from frontend.main_window import MainWindow
from frontend.reception_dashboard import ReceptionDashboard
from frontend.views.book_for_patient_view import BookForPatientView
from frontend.views.booking_view import BookingView
from frontend.views.common import BaseApiView
from frontend.views.medical_result_view import MedicalResultView
from frontend.views.payment_view import PaymentView


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def test_central_patient_logout_returns_control_to_main_login(
    qt_app: QApplication,
) -> None:
    session = SessionState()
    client = MagicMock(spec=ApiClient)
    window = MainWindow(client, session, central_auth=True)
    emitted: list[bool] = []
    window.logout_requested.connect(lambda: emitted.append(True))
    window.login_as("token", {"username": "patient01", "role": "PATIENT"})

    window._logout()

    assert emitted == [True]
    assert not session.is_authenticated
    client.clear_access_token.assert_called_once()
    window.deleteLater()
    qt_app.processEvents()


def test_language_change_keeps_loaded_medical_record(
    qt_app: QApplication,
) -> None:
    view = MedicalResultView(MagicMock(spec=ApiClient))
    view._medical_record_id = 42
    view._appointment_id = 17
    view.values["diagnosis"].setText("Chẩn đoán cần được giữ nguyên")
    view.prescription_model.appendRow([QStandardItem("Thuốc A")])

    view.retranslate_ui()

    assert view._medical_record_id == 42
    assert view._appointment_id == 17
    assert view.values["diagnosis"].text() == "Chẩn đoán cần được giữ nguyên"
    assert view.prescription_model.rowCount() == 1
    view.deleteLater()
    qt_app.processEvents()


def test_staff_booking_panels_reflow_to_one_column(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BookForPatientView, "_load_doctors", lambda _self: None)
    view = BookForPatientView(MagicMock(spec=ApiClient))

    view.resize(900, 700)
    view._reflow_content(force=True)
    narrow = view.content_grid.getItemPosition(view.content_grid.indexOf(view.right_col))

    view.resize(1100, 700)
    view._reflow_content(force=True)
    wide = view.content_grid.getItemPosition(view.content_grid.indexOf(view.right_col))

    assert narrow[:2] == (1, 0)
    assert wide[:2] == (0, 1)
    view.deleteLater()
    qt_app.processEvents()


def test_staff_booking_fits_real_minimum_shell_without_horizontal_overflow(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    client = MagicMock(spec=ApiClient)
    client.token = "staff-token"
    window = ReceptionDashboard(client)
    window.resize(1100, 680)
    window.show()
    window.navigate_by_route("book_for_patient")
    qt_app.processEvents()

    view = window.view_book
    viewport = view.scroll_area.viewport()
    content = view.scroll_area.widget()

    assert view._content_columns == 1
    assert (
        view.scroll_area.horizontalScrollBarPolicy()
        is Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    assert view.scroll_area.horizontalScrollBar().maximum() == 0
    assert content is not None
    assert content.width() <= viewport.width()

    overflowing: list[tuple[str, int, int]] = []
    for child in content.findChildren(QWidget):
        if not child.isVisibleTo(content):
            continue
        position = child.mapTo(viewport, QPoint(0, 0))
        if position.x() < -1 or position.x() + child.width() > viewport.width() + 1:
            overflowing.append((child.objectName(), position.x(), child.width()))

    assert overflowing == []
    window.close()
    window.deleteLater()
    qt_app.processEvents()


def test_staff_and_patient_sidebar_transitions_keep_page_layout_stable(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)

    staff_client = MagicMock(spec=ApiClient)
    staff_client.token = "staff-token"
    staff = ReceptionDashboard(staff_client)
    staff.show()
    staff.navigate_by_route("book_for_patient")

    staff.resize(staff.SIDEBAR_COMPACT_BREAKPOINT - 1, 680)
    qt_app.processEvents()
    assert staff.sidebar.is_compact
    assert staff.view_book._content_columns == 2

    staff.resize(staff.SIDEBAR_COMPACT_BREAKPOINT, 680)
    qt_app.processEvents()
    assert not staff.sidebar.is_compact
    assert staff.view_book._content_columns == 2
    assert staff.view_book.scroll_area.horizontalScrollBar().maximum() == 0

    patient_client = MagicMock(spec=ApiClient)
    patient = MainWindow(patient_client, SessionState(), central_auth=True)
    patient.login_as("patient-token", {"username": "patient01", "role": "PATIENT"})
    patient.show()

    patient.resize(patient.SIDEBAR_COMPACT_BREAKPOINT - 1, 680)
    qt_app.processEvents()
    assert patient.sidebar.is_compact
    assert patient.dashboard_view._stat_columns == 4

    patient.resize(patient.SIDEBAR_COMPACT_BREAKPOINT, 680)
    qt_app.processEvents()
    assert not patient.sidebar.is_compact
    assert patient.dashboard_view._stat_columns == 4

    staff.close()
    staff.deleteLater()
    patient.close()
    patient.deleteLater()
    qt_app.processEvents()


def test_patient_booking_grids_reflow_at_supported_widths(
    qt_app: QApplication,
) -> None:
    view = BookingView(MagicMock(spec=ApiClient))
    cards = [QFrame(view.spec_grid_widget), QFrame(view.spec_grid_widget)]
    view._specialty_cards = cards

    view.resize(900, 700)
    view._layout_specialty_cards(force=True)
    narrow_positions = [
        view.spec_grid_layout.getItemPosition(view.spec_grid_layout.indexOf(card))[:2]
        for card in cards
    ]

    view.resize(1100, 700)
    view._layout_specialty_cards(force=True)
    wide_positions = [
        view.spec_grid_layout.getItemPosition(view.spec_grid_layout.indexOf(card))[:2]
        for card in cards
    ]

    slot_buttons = [QPushButton("08:00"), QPushButton("08:30"), QPushButton("09:00")]
    view._slot_widgets = slot_buttons
    view.resize(900, 700)
    view._layout_slot_buttons(force=True)
    slot_positions = [
        view.slots_layout.getItemPosition(view.slots_layout.indexOf(button))[:2]
        for button in slot_buttons
    ]

    assert narrow_positions == [(0, 0), (1, 0)]
    assert wide_positions == [(0, 0), (0, 1)]
    assert slot_positions == [(0, 0), (0, 1), (1, 0)]
    view.deleteLater()
    qt_app.processEvents()


def test_cash_payment_rejects_insufficient_tender(
    qt_app: QApplication,
) -> None:
    view = PaymentView(MagicMock(spec=ApiClient))
    view._current_invoice = {"invoice_id": 7, "total_amount": 200_000}
    view.rb_cash.setChecked(True)
    view.cash_input.setText("100000")
    view.run_api_task = MagicMock()  # type: ignore[method-assign]

    view._process_payment()

    view.run_api_task.assert_not_called()
    assert view.feedback.title == "Số tiền chưa đủ"
    assert not view.feedback.isHidden()
    view.deleteLater()
    qt_app.processEvents()
