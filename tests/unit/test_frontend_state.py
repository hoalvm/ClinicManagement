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
from frontend.views.common import BaseApiView, table_item
from frontend.views.invoice_detail_view import InvoiceDetailView
from frontend.views.medical_result_view import MedicalResultView
from frontend.views.patient_profile_view import NULL_DATE, PatientProfileView
from frontend.views.register_view import RegisterView


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
