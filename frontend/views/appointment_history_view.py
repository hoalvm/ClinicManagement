"""Paginated appointment history."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import (
    BaseApiView,
    configure_table,
    format_date,
    format_time,
    require_page,
    table_item,
)
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import PaginationWidget
from frontend.widgets.status_badge import StatusBadgeDelegate


class AppointmentHistoryView(BaseApiView):
    appointment_requested = Signal(int)
    book_requested = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        self._total_appointments = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        self.header = PageHeader(t("appointment_history_title"), t("appointment_history_subtitle"))
        self.book_button = QPushButton(t("btn_new_booking"))
        self.book_button.setObjectName("primaryButton")
        self.book_button.clicked.connect(self.book_requested.emit)
        self.header.add_action(self.book_button)
        root.addWidget(self.header)

        filter_card = QFrame()
        filter_card.setObjectName("filterBar")
        filters = QGridLayout(filter_card)
        filters.setContentsMargins(16, 16, 16, 16)
        filters.setHorizontalSpacing(10)
        filters.setVerticalSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText(t("appointment_search_placeholder"))
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search appointment history")
        filters.addWidget(self.search, 0, 0, 1, 5)

        self.status_label = QLabel(t("field_payment_status"))
        self.status_label.setObjectName("fieldLabel")
        self.status = QComboBox()
        self.status.setMinimumWidth(170)
        self.status.setAccessibleName("Filter appointments by status")
        self._populate_status_combo()
        self.status_label.setBuddy(self.status)

        self.refresh_button = QPushButton(t("btn_refresh"))
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setAccessibleName("Refresh appointment history")
        self.details_button = QPushButton(t("btn_view_details"))
        self.details_button.setObjectName("primaryButton")
        self.details_button.setAccessibleName("View selected appointment details")
        self.details_button.setEnabled(False)

        filters.addWidget(self.status_label, 1, 0)
        filters.addWidget(self.status, 1, 1)
        filters.setColumnStretch(2, 1)
        filters.addWidget(self.refresh_button, 1, 3)
        filters.addWidget(self.details_button, 1, 4)
        root.addWidget(filter_card)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.table.setAccessibleName("Appointment history results")
        self.table.setAccessibleDescription(
            "Select an appointment and press Enter to open its details."
        )
        self.model: QStandardItemModel = configure_table(
            self.table,
            [
                t("field_date"),
                t("field_time"),
                t("field_doctor"),
                t("field_specialty"),
                t("field_clinic"),
                t("field_reason"),
                t("field_payment_status"),
            ],
            stretch_column=5,
            column_widths={0: 112, 1: 120, 2: 170, 3: 150, 4: 190, 6: 132},
        )
        self.table.setItemDelegateForColumn(6, StatusBadgeDelegate(self.table))

        self.empty_state = EmptyState(
            t("no_appointments_found"),
            t("no_appointments_desc"),
            action_text=t("btn_refresh"),
        )
        self.empty_state.setAccessibleName("No appointment results")

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.table)
        self.content_stack.addWidget(self.empty_state)
        self.content_stack.setCurrentWidget(self.table)
        root.addWidget(self.content_stack, 1)

        self.pagination = PaginationWidget()
        self.pagination.setAccessibleName("Appointment history pagination")
        root.addWidget(self.pagination)

        self.search.returnPressed.connect(self._search)
        self.status.currentIndexChanged.connect(self._filter_changed)
        self.refresh_button.clicked.connect(self._search)
        self.details_button.clicked.connect(self._open_selected)
        self.table.activated.connect(self._open_index)
        self.table.selectionModel().selectionChanged.connect(
            lambda *_args: self._sync_details_button()
        )
        self.empty_state.action_requested.connect(self._retry)
        self.pagination.page_changed.connect(self._change_page)
        self.pagination.page_size_changed.connect(self._page_size_changed)

        get_i18n().language_changed.connect(self.retranslate_ui)

    def _populate_status_combo(self) -> None:
        status_items = [
            (t("status_all"), "All"),
            (t("status_pending"), "PENDING"),
            (t("status_confirmed"), "CONFIRMED"),
            (t("status_checked_in"), "CHECKED_IN"),
            (t("status_in_progress"), "IN_PROGRESS"),
            (t("status_completed"), "COMPLETED"),
            (t("status_cancelled"), "CANCELLED"),
        ]
        curr_data = self.status.currentData()
        self.status.blockSignals(True)
        self.status.clear()
        for label, val in status_items:
            self.status.addItem(label, val)
        idx = self.status.findData(curr_data)
        if idx >= 0:
            self.status.setCurrentIndex(idx)
        self.status.blockSignals(False)

    def retranslate_ui(self) -> None:
        """Update all text in AppointmentHistoryView according to current language."""
        self.header.set_title(t("appointment_history_title"))
        if self._total_appointments > 0:
            self.header.set_subtitle(t("appointments_count", count=self._total_appointments))
        else:
            self.header.set_subtitle(t("appointment_history_subtitle"))
        self.book_button.setText(t("btn_new_booking"))
        self.search.setPlaceholderText(t("appointment_search_placeholder"))
        self.status_label.setText(t("field_payment_status"))
        self._populate_status_combo()
        self.refresh_button.setText(t("btn_refresh"))
        self.details_button.setText(t("btn_view_details"))
        self.empty_state.set_title(t("no_appointments_found"))
        self.empty_state.set_description(t("no_appointments_desc"))
        self.empty_state.set_action(t("btn_refresh"))

        headers = [
            t("field_date"),
            t("field_time"),
            t("field_doctor"),
            t("field_specialty"),
            t("field_clinic"),
            t("field_reason"),
            t("field_payment_status"),
        ]
        for col, h in enumerate(headers):
            self.model.setHeaderData(col, Qt.Orientation.Horizontal, h)

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        params: dict[str, object] = {
            "page": self._page,
            "page_size": self.pagination.page_size,
        }
        keyword = self.search.text().strip()
        if keyword:
            params["keyword"] = keyword
        status_val = self.status.currentData() or "All"
        if status_val != "All":
            params["status"] = status_val

        self.content_stack.setCurrentWidget(self.table)
        self.details_button.setEnabled(False)
        self.run_api_task(
            "appointments",
            lambda: self.api_client.get("/api/v1/appointments/me", params=params),
            self._render,
            controls=(
                self.search,
                self.status,
                self.refresh_button,
                self.details_button,
                self.table,
                self.empty_state.action_button,
                self.pagination,
            ),
            loading_text=t("loading"),
            on_finished=self._sync_details_button,
        )

    def _render(self, payload: object) -> None:
        page = require_page(payload)
        items = page["items"]
        self.model.removeRows(0, self.model.rowCount())
        for appointment in items:
            doctor = appointment.get("doctor") or {}
            clinic = appointment.get("clinic") or {}
            appointment_id = int(appointment["appointment_id"])
            start = format_time(appointment.get("start_time"))
            end = format_time(appointment.get("end_time"))
            self.model.appendRow(
                [
                    table_item(
                        format_date(appointment.get("appointment_date")),
                        user_data=appointment_id,
                    ),
                    table_item(f"{start} - {end}"),
                    table_item(doctor.get("full_name")),
                    table_item(doctor.get("specialty")),
                    table_item(clinic.get("clinic_name")),
                    table_item(appointment.get("reason")),
                    table_item(appointment.get("status")),
                ]
            )

        self._page = int(page.get("page", self._page))
        total = int(page.get("total", 0))
        self._total_appointments = total
        self.pagination.set_page(
            self._page,
            int(page.get("total_pages", 0)),
            total,
        )
        self.header.set_subtitle(t("appointments_count", count=total))
        self.table.clearSelection()
        self.details_button.setEnabled(False)
        self.content_stack.setCurrentWidget(self.table if items else self.empty_state)

    def _selected_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows(0)
        if not indexes:
            return None
        value = indexes[0].data(role=Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _open_selected(self) -> None:
        appointment_id = self._selected_id()
        if appointment_id is not None:
            self.appointment_requested.emit(appointment_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=Qt.ItemDataRole.UserRole)
        if value is not None:
            self.appointment_requested.emit(int(value))

    def _search(self) -> None:
        self._page = 1
        self.load()

    def _retry(self) -> None:
        self._page = 1
        self.load()

    def _filter_changed(self, _index: int = 0) -> None:
        self._page = 1
        self.load()

    def _change_page(self, page: int) -> None:
        self._page = page
        self.load()

    def _page_size_changed(self, _size: int) -> None:
        self._page = 1
        self.load()

    def _sync_details_button(self) -> None:
        has_selection = bool(self.table.selectionModel().selectedRows())
        self.details_button.setEnabled(not self._workers and has_selection)

    def clear_data(self) -> None:
        self._page = 1
        self._total_appointments = 0
        self.search.clear()
        was_blocked = self.status.blockSignals(True)
        try:
            self.status.setCurrentIndex(0)
        finally:
            self.status.blockSignals(was_blocked)
        self.model.removeRows(0, self.model.rowCount())
        self.table.clearSelection()
        self.pagination.reset()
        self.header.set_subtitle(t("appointment_history_subtitle"))
        self.content_stack.setCurrentWidget(self.table)
        self.details_button.setEnabled(False)
