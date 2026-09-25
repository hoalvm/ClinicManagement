"""Regression tests for patient profile and pending-task UI state."""

from collections.abc import Iterator
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from frontend.api.api_client import ApiClient
from frontend.core.session import SessionState
from frontend.main_window import MainWindow
from frontend.views.appointment_detail_view import AppointmentDetailView
from frontend.views.appointment_history_view import AppointmentHistoryView
from frontend.views.common import BaseApiView, table_item
from frontend.views.dashboard_view import DashboardView
from frontend.views.invoice_detail_view import InvoiceDetailView
from frontend.views.invoice_history_view import InvoiceHistoryView
from frontend.views.medical_history_view import MedicalHistoryView
from frontend.views.medical_result_view import MedicalResultView
from frontend.views.patient_profile_view import NULL_DATE, PatientProfileView
from frontend.views.register_view import RegisterView
from frontend.widgets.sidebar import Sidebar


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def test_profile_renders_null_demographics_and_merges_session(
    qt_app: QApplication,
) -> None:
    session = SessionState()
    session.set_authenticated(
        "signed-token",
        {
            "user_id": 11,
            "patient_id": 21,
            "username": "patient11",
            "full_name": "Old Name",
            "role": "PATIENT",
            "is_active": True,
        },
    )
    view = PatientProfileView(MagicMock(spec=ApiClient), session)
    profile = {
        "patient_id": 21,
        "username": "patient11",
        "full_name": "Updated Name",
        "phone": None,
        "email": None,
        "date_of_birth": None,
        "gender": None,
        "address": None,
    }

    view._render(profile)

    assert view.date_of_birth.date() == NULL_DATE
    assert view.gender.currentData() is None
    assert session.current_user == {
        "user_id": 11,
        "patient_id": 21,
        "username": "patient11",
        "full_name": "Updated Name",
        "phone": None,
        "email": None,
        "date_of_birth": None,
        "gender": None,
        "address": None,
        "role": "PATIENT",
        "is_active": True,
    }
    view.deleteLater()
    qt_app.processEvents()


def test_invalidating_pending_task_restores_disabled_controls(
    qt_app: QApplication,
) -> None:
    view = BaseApiView(MagicMock(spec=ApiClient))
    control = QPushButton("Save", view)
    control.setEnabled(False)
    view.loading.start("Saving")
    view._handlers[("save-profile", 0)] = SimpleNamespace(controls=(control,))

    view.invalidate_pending()

    assert control.isEnabled()
    assert view.loading.isHidden()
    assert view._generation == 1
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_type", "id_attribute"),
    [
        (AppointmentDetailView, "_appointment_id"),
        (MedicalResultView, "_medical_record_id"),
        (InvoiceDetailView, "_invoice_id"),
    ],
)
def test_detail_activation_invalidates_stale_request_generation(
    qt_app: QApplication,
    view_type: type[BaseApiView],
    id_attribute: str,
) -> None:
    view = view_type(MagicMock(spec=ApiClient))
    view.load = MagicMock()

    view.activate(101)
    view.activate(202)

    assert view._generation == 2
    assert getattr(view, id_attribute) == 202
    assert view.load.call_count == 2
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_type", "id_attribute"),
    [
        (AppointmentDetailView, "_appointment_id"),
        (MedicalResultView, "_medical_record_id"),
        (InvoiceDetailView, "_invoice_id"),
    ],
)
def test_detail_activation_clears_content_and_old_link_targets(
    qt_app: QApplication,
    view_type: type[BaseApiView],
    id_attribute: str,
) -> None:
    view = view_type(MagicMock(spec=ApiClient))
    view.load = MagicMock()
    for value in view.values.values():
        value.setText("previous patient data")

    if isinstance(view, AppointmentDetailView):
        view._medical_record_id = 71
        view._invoice_id = 81
        view.medical_button.show()
        view.invoice_button.show()
    elif isinstance(view, MedicalResultView):
        view._appointment_id = 61
        view.prescription_model.appendRow([table_item("previous prescription")])
        view.appointment_button.show()
    else:
        view._appointment_id = 61
        view.items_model.appendRow([table_item("previous invoice item")])
        view.payment_values["amount"].setText("999 VND")
        view.payment_card.show()
        view.appointment_button.show()

    view.activate(202)

    assert getattr(view, id_attribute) == 202
    assert all(value.text() == "—" for value in view.values.values())
    if isinstance(view, AppointmentDetailView):
        assert view._medical_record_id is None
        assert view._invoice_id is None
        assert view.medical_button.isHidden()
        assert view.invoice_button.isHidden()
    elif isinstance(view, MedicalResultView):
        assert view._appointment_id is None
        assert view.prescription_model.rowCount() == 0
        assert view.appointment_button.isHidden()
    else:
        assert view._appointment_id is None
        assert view.items_model.rowCount() == 0
        assert all(value.text() == "—" for value in view.payment_values.values())
        assert view.payment_card.isHidden()
        assert view.appointment_button.isHidden()
    view.deleteLater()
    qt_app.processEvents()


def test_leaving_registration_clears_credentials_and_personal_data(
    qt_app: QApplication,
) -> None:
    view = RegisterView(MagicMock(spec=ApiClient))
    view.username.setText("patient03")
    view.password.setText("TopSecret123!")
    view.confirm_password.setText("TopSecret123!")
    view.full_name.setText("Patient Three")
    view.address.setPlainText("Private address")

    view.clear_data()

    assert view.username.text() == ""
    assert view.password.text() == ""
    assert view.confirm_password.text() == ""
    assert view.full_name.text() == ""
    assert view.address.toPlainText() == ""
    view.deleteLater()
    qt_app.processEvents()


def test_switching_patient_pages_invalidates_page_being_left(qt_app: QApplication) -> None:
    window = MainWindow(MagicMock(spec=ApiClient), SessionState())
    window.page_stack.setCurrentWidget(window.dashboard_view)

    window._show_patient_page(window.profile_view)

    assert window.dashboard_view._generation == 1
    assert window.page_stack.currentWidget() is window.profile_view
    window.deleteLater()
    qt_app.processEvents()


def test_table_item_tooltip_preserves_full_elided_text() -> None:
    text = "Take one tablet twice daily after meals for ten days"

    item = table_item(text)

    assert item.text() == text
    assert item.toolTip() == text


def test_registration_and_profile_addresses_use_tab_for_focus_navigation(
    qt_app: QApplication,
) -> None:
    """Multiline address fields must not trap keyboard-only users."""

    register = RegisterView(MagicMock(spec=ApiClient))
    profile = PatientProfileView(MagicMock(spec=ApiClient), SessionState())

    assert register.address.tabChangesFocus()
    assert profile.address.tabChangesFocus()

    register.deleteLater()
    profile.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_type", "filter_attribute", "filter_name", "table_name"),
    [
        (
            AppointmentHistoryView,
            "search",
            "Search appointment history",
            "Appointment history results",
        ),
        (
            MedicalHistoryView,
            "search",
            "Search medical history",
            "Medical history results",
        ),
        (
            InvoiceHistoryView,
            "status",
            "Filter invoices by payment status",
            "Invoice history results",
        ),
    ],
)
def test_history_filters_and_tables_have_accessible_names(
    qt_app: QApplication,
    view_type: type[BaseApiView],
    filter_attribute: str,
    filter_name: str,
    table_name: str,
) -> None:
    view = view_type(MagicMock(spec=ApiClient))
    filter_control = getattr(view, filter_attribute)

    assert filter_control.accessibleName() == filter_name
    assert view.table.accessibleName() == table_name
    assert "Enter" in view.table.accessibleDescription()
    assert view.refresh_button.accessibleName()
    assert view.details_button.accessibleName()

    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_type", "signal_attribute", "record_id"),
    [
        (AppointmentHistoryView, "appointment_requested", 101),
        (MedicalHistoryView, "medical_record_requested", 202),
        (InvoiceHistoryView, "invoice_requested", 303),
    ],
)
def test_activating_history_row_opens_its_record(
    qt_app: QApplication,
    view_type: type[BaseApiView],
    signal_attribute: str,
    record_id: int,
) -> None:
    view = view_type(MagicMock(spec=ApiClient))
    received: list[int] = []
    getattr(view, signal_attribute).connect(received.append)
    row = [table_item("Record", user_data=record_id)]
    row.extend(table_item("") for _ in range(view.model.columnCount() - 1))
    view.model.appendRow(row)

    view.table.activated.emit(view.model.index(0, view.model.columnCount() - 1))

    assert received == [record_id]
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_type", "id_attribute"),
    [
        (AppointmentDetailView, "_appointment_id"),
        (MedicalResultView, "_medical_record_id"),
        (InvoiceDetailView, "_invoice_id"),
    ],
)
def test_detail_back_remains_available_while_request_starts(
    qt_app: QApplication,
    view_type: type[BaseApiView],
    id_attribute: str,
) -> None:
    view = view_type(MagicMock(spec=ApiClient))
    captured_controls: tuple[QPushButton, ...] = ()

    def start_pending_task(
        _key: str,
        _operation: object,
        _on_success: object,
        *,
        controls: tuple[QPushButton, ...] = (),
        **_kwargs: object,
    ) -> None:
        nonlocal captured_controls
        captured_controls = controls
        for control in controls:
            control.setEnabled(False)

    view.run_api_task = start_pending_task  # type: ignore[method-assign]
    setattr(view, id_attribute, 42)
    view.back_button.setEnabled(True)

    view.load()

    assert view.back_button not in captured_controls
    assert view.back_button.isEnabled()
    view.deleteLater()
    qt_app.processEvents()


@pytest.mark.parametrize(
    ("view_factory", "empty_attribute"),
    [
        (
            lambda: MedicalResultView(MagicMock(spec=ApiClient)),
            "no_prescription",
        ),
        (lambda: InvoiceDetailView(MagicMock(spec=ApiClient)), "not_paid"),
        (lambda: DashboardView(MagicMock(spec=ApiClient)), "no_upcoming"),
    ],
)
def test_detail_empty_states_are_hidden_before_successful_response(
    qt_app: QApplication,
    view_factory: object,
    empty_attribute: str,
) -> None:
    view = view_factory()

    assert getattr(view, empty_attribute).isHidden()

    view.deleteLater()
    qt_app.processEvents()


def test_sidebar_compact_mode_preserves_icon_navigation_accessibility(
    qt_app: QApplication,
) -> None:
    sidebar = Sidebar()

    assert sidebar.width() == Sidebar.EXPANDED_WIDTH
    assert not sidebar.is_compact
    for route, label in Sidebar._ITEMS:
        button = sidebar._buttons[route]
        assert button.text() == label
        assert button.accessibleName() == label
        assert not button.icon().isNull()

    sidebar.set_compact(True)

    assert sidebar.width() == Sidebar.COMPACT_WIDTH
    assert sidebar.is_compact
    for route, label in Sidebar._ITEMS:
        button = sidebar._buttons[route]
        assert button.text() == ""
        assert button.accessibleName() == label
        assert button.toolTip() == label
        assert not button.icon().isNull()
    assert sidebar.logout_button.accessibleName() == "Log out"

    sidebar.set_compact(False)

    assert sidebar.width() == Sidebar.EXPANDED_WIDTH
    assert not sidebar.is_compact
    assert all(sidebar._buttons[route].text() == label for route, label in Sidebar._ITEMS)
    sidebar.deleteLater()
    qt_app.processEvents()


def test_dashboard_stat_cards_reflow_for_wide_and_narrow_layouts(
    qt_app: QApplication,
) -> None:
    dashboard = DashboardView(MagicMock(spec=ApiClient))

    dashboard.resize(1100, 700)
    dashboard._reflow_stats(force=True)
    wide_positions = [
        dashboard.cards.getItemPosition(dashboard.cards.indexOf(card))[:2]
        for card in dashboard._stat_cards
    ]

    assert dashboard._stat_columns == 4
    assert wide_positions == [(0, 0), (0, 1), (0, 2), (0, 3)]

    dashboard.resize(900, 700)
    dashboard._reflow_stats(force=True)
    narrow_positions = [
        dashboard.cards.getItemPosition(dashboard.cards.indexOf(card))[:2]
        for card in dashboard._stat_cards
    ]

    assert dashboard._stat_columns == 2
    assert narrow_positions == [(0, 0), (0, 1), (1, 0), (1, 1)]
    dashboard.deleteLater()
    qt_app.processEvents()


def test_appointment_detail_renders_backend_payload_without_key_error(
    qt_app: QApplication,
) -> None:
    view = AppointmentDetailView(MagicMock(spec=ApiClient))
    payload = {
        "appointment_id": 42,
        "appointment_date": "2026-03-25",
        "start_time": "09:00:00",
        "end_time": "09:30:00",
        "status": "CONFIRMED",
        "reason": "General checkup",
        "doctor": {
            "doctor_id": 1,
            "full_name": "Dr. Strange",
            "specialty": "Neurology",
            "phone": "0901234567",
            "email": "strange@clinic.com",
            "license_number": "MED-999",
        },
        "clinic": {
            "clinic_id": 1,
            "clinic_name": "Central Clinic",
            "address": "123 Main St",
            "phone": "0243999999",
        },
        "medical_record_id": 10,
        "invoice_id": 20,
    }

    view._render(payload)

    assert view._appointment_id == 42
    assert view._medical_record_id == 10
    assert view._invoice_id == 20
    assert view.header.subtitle_label.text() == "#000042"
    assert view.values["reason"].text() == "General checkup"
    assert view.values["doctor_name"].text() == "Dr. Strange"
    assert not view.medical_button.isHidden()
    assert not view.invoice_button.isHidden()
    assert not view.reschedule_button.isHidden()
    assert not view.cancel_button.isHidden()
    view.deleteLater()
    qt_app.processEvents()


def test_invoice_detail_renders_backend_payload_without_key_error(
    qt_app: QApplication,
) -> None:
    view = InvoiceDetailView(MagicMock(spec=ApiClient))
    payload = {
        "invoice_id": 88,
        "appointment_id": 42,
        "created_at": "2026-03-25T10:00:00",
        "total_amount": "250000",
        "status": "PAID",
        "appointment": {
            "appointment_date": "2026-03-25",
            "start_time": "09:00:00",
            "doctor": {
                "doctor_id": 1,
                "full_name": "Dr. Strange",
            },
        },
        "items": [
            {
                "item_name": "Consultation",
                "quantity": 1,
                "unit_price": "250000",
                "line_total": "250000",
            }
        ],
        "payment": {
            "payment_id": 5,
            "amount": "250000",
            "payment_method": "CASH",
            "payment_date": "2026-03-25T10:05:00",
        },
    }

    view._render(payload)

    assert view._appointment_id == 42
    assert view.values["doctor"].text() == "Dr. Strange"
    assert view.items_model.rowCount() == 1
    assert view.payment_values["method"].text() == "CASH"
    view.deleteLater()
    qt_app.processEvents()
