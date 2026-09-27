"""Regression coverage for Staff adaptive operational tables."""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import ViewState
from frontend.views.appointment_management_view import AppointmentManagementView
from frontend.views.check_in_view import CheckInView
from frontend.views.common import BaseApiView
from frontend.views.invoice_view import InvoiceManagementView
from frontend.views.payment_history_view import PaymentHistoryView
from frontend.widgets.adaptive_data_table import (
    RAW_VALUE_ROLE,
    SECONDARY_TEXT_ROLE,
    AdaptiveDataTable,
)


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture
def staff_views(monkeypatch: pytest.MonkeyPatch) -> tuple[BaseApiView, ...]:
    monkeypatch.setattr(BaseApiView, "run_api_task", lambda *_args, **_kwargs: False)
    client = MagicMock(spec=ApiClient)
    return (
        AppointmentManagementView(client),
        CheckInView(client),
        InvoiceManagementView(client),
        PaymentHistoryView(client),
    )


def test_operational_lists_use_adaptive_read_only_tables_and_state_hosts(
    qt_app: QApplication,
    staff_views: tuple[BaseApiView, ...],
) -> None:
    for view in staff_views:
        table = (
            view.results_table
            if isinstance(view, CheckInView)
            else view.table
        )
        assert isinstance(table, AdaptiveDataTable)
        assert view.state_host is not None
        assert view.state_host.content_widget is table
        assert table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
        assert sum(spec.stretch for spec in table.column_specs) == 1
        assert all(spec.minimum_width >= 40 for spec in table.column_specs)
        view.deleteLater()
    qt_app.processEvents()


def test_empty_error_and_retry_are_distinct_for_every_staff_list(
    qt_app: QApplication,
    staff_views: tuple[BaseApiView, ...],
) -> None:
    appointment, check_in, invoice, payment = staff_views
    appointment._on_appointments_loaded({"items": [], "total": 0, "total_pages": 0})
    check_in._on_candidates_loaded({"items": []})
    invoice._on_invoices_loaded({"items": [], "total": 0, "total_pages": 0})
    payment._on_payments_loaded({"items": [], "total": 0, "total_pages": 0})

    for view in staff_views:
        assert view.state_host is not None
        assert view.state_host.state is ViewState.EMPTY
        view.state_host.show_error("Mất kết nối", "Không thể tải dữ liệu.")
        assert view.state_host.state is ViewState.ERROR
        view.run_api_task = MagicMock(return_value=False)  # type: ignore[method-assign]
        view.state_host.retry_requested.emit()
        view.run_api_task.assert_called_once()
        view.deleteLater()
    qt_app.processEvents()


def test_status_and_primary_actions_stay_visible_at_staff_minimum_width(
    qt_app: QApplication,
    staff_views: tuple[BaseApiView, ...],
) -> None:
    appointment, check_in, invoice, payment = staff_views
    long_name = "Nguyễn Văn Một Hai Ba Bốn Năm Sáu Bảy Tám Chín Mười Rất Dài"
    appt = {
        "appointment_id": 123456,
        "appointment_date": "2026-09-27",
        "start_time": "10:30:00",
        "status": "PENDING",
        "patient": {"full_name": long_name, "phone": "0912345678"},
        "doctor": {"full_name": long_name},
    }
    invoice_data = {
        "invoice_id": 123456,
        "appointment_id": 987654,
        "patient_name": long_name,
        "patient_phone": "0912345678",
        "doctor_name": long_name,
        "total_amount": 999_999_999,
        "status": "UNPAID",
    }
    appointment._on_appointments_loaded(
        {"items": [appt], "total": 1, "total_pages": 1}
    )
    check_in._on_candidates_loaded({"items": [appt]})
    invoice._on_invoices_loaded(
        {"items": [invoice_data], "total": 1, "total_pages": 1}
    )
    payment._on_payments_loaded(
        {
            "items": [
                {
                    "payment_id": 123456,
                    "invoice_id": 987654,
                    "patient_name": long_name,
                    "doctor_name": long_name,
                    "amount": 999_999_999,
                    "payment_method": "CARD",
                    "payment_date": "2026-09-27T10:30:00",
                }
            ],
            "total": 1,
            "total_pages": 1,
        }
    )

    for view in staff_views:
        view.resize(1022, 680)
        view.show()
    qt_app.processEvents()

    action_tables = (
        (appointment.table, 4, 5),
        (check_in.results_table, 4, 5),
        (invoice.table, 5, 6),
    )
    for table, status_column, action_column in action_tables:
        assert table.horizontalScrollBar().maximum() == 0
        assert table.model().index(0, status_column).data(RAW_VALUE_ROLE) in {
            "PENDING",
            "UNPAID",
        }
        action_widget = table.indexWidget(table.model().index(0, action_column))
        assert action_widget is not None
        assert action_widget.findChild(QPushButton) is not None
        action_rect = table.visualRect(table.model().index(0, action_column))
        assert table.viewport().rect().contains(action_rect.center())

    assert payment.table.horizontalScrollBar().maximum() == 0
    assert (
        appointment.table.model().index(0, 2).data(SECONDARY_TEXT_ROLE)
        == "0912345678"
    )
    assert (
        invoice.table.model().index(0, 0).data(SECONDARY_TEXT_ROLE)
        == "Hẹn #987654"
    )
    assert (
        payment.table.model().index(0, 0).data(SECONDARY_TEXT_ROLE)
        == "INV-987654"
    )
    for view in staff_views:
        view.close()
        view.deleteLater()
    qt_app.processEvents()


def test_load_requests_disable_every_filter_control(
    qt_app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_controls: list[tuple[object, ...]] = []

    def capture_task(
        _self: BaseApiView,
        _key: str,
        _operation: object,
        _on_success: object,
        **kwargs: object,
    ) -> bool:
        captured_controls.append(tuple(kwargs.get("controls", ())))
        return False

    monkeypatch.setattr(BaseApiView, "run_api_task", capture_task)
    client = MagicMock(spec=ApiClient)
    views = (
        AppointmentManagementView(client),
        CheckInView(client),
        InvoiceManagementView(client),
        PaymentHistoryView(client),
    )
    for view in views:
        if isinstance(view, AppointmentManagementView):
            view.load_appointments()
            required = {view.search_input, view.status_combo, view.btn_refresh}
        elif isinstance(view, CheckInView):
            view.search_and_load()
            required = {view.search_input, view.queue_num_input, view.btn_search}
        elif isinstance(view, InvoiceManagementView):
            view.load_invoices()
            required = {view.search_input, view.status_combo, view.btn_filter}
        else:
            view.load_payments()
            required = {view.search_input, view.method_combo, view.btn_filter}
        assert required.issubset(set(captured_controls[-1]))
        view.deleteLater()
    qt_app.processEvents()


def test_invoice_item_validation_rejects_invalid_numbers(
    qt_app: QApplication,
) -> None:
    table = QTableWidget(1, 3)
    table.setItem(0, 0, QTableWidgetItem("Khám chuyên khoa"))
    table.setItem(0, 1, QTableWidgetItem("không-phải-số"))
    table.setItem(0, 2, QTableWidgetItem("200000"))

    with pytest.raises(ValueError, match="Số lượng"):
        InvoiceManagementView._collect_invoice_items(table)

    table.setItem(0, 1, QTableWidgetItem("1"))
    table.setItem(0, 2, QTableWidgetItem("-1"))
    with pytest.raises(ValueError, match="không âm"):
        InvoiceManagementView._collect_invoice_items(table)

    table.deleteLater()
    qt_app.processEvents()

