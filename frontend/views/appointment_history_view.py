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
from frontend.ui.icons import apply_line_icon, line_icon
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

    _DEFAULT_SUBTITLE = "Find and review your upcoming and previous clinic visits."

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        self.header = PageHeader("Appointment History", self._DEFAULT_SUBTITLE)
        root.addWidget(self.header)

        filter_card = QFrame()
        filter_card.setObjectName("filterBar")
        filters = QGridLayout(filter_card)
        filters.setContentsMargins(16, 16, 16, 16)
        filters.setHorizontalSpacing(10)
        filters.setVerticalSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search doctor, specialty, clinic, or reason")
        self.search.setClearButtonEnabled(True)
        self.search.setAccessibleName("Search appointment history")
        search_action = self.search.addAction(
            line_icon("search", "#64748B", active_color="#0F766E"),
            QLineEdit.ActionPosition.LeadingPosition,
        )
        search_action.setToolTip("Search appointments")
        filters.addWidget(self.search, 0, 0, 1, 5)

        status_label = QLabel("Status")
        status_label.setObjectName("fieldLabel")
        self.status = QComboBox()
        self.status.setMinimumWidth(170)
        self.status.setAccessibleName("Filter appointments by status")
        self.status.addItems(
            [
                "All",
                "PENDING",
                "CONFIRMED",
                "CHECKED_IN",
                "IN_PROGRESS",
                "COMPLETED",
                "CANCELLED",
            ]
        )
        status_label.setBuddy(self.status)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        apply_line_icon(
            self.refresh_button,
            "refresh",
            active_color="#0F766E",
            accessible_name="Refresh appointment history",
        )
        self.details_button = QPushButton("View Details")
        self.details_button.setObjectName("primaryButton")
        self.details_button.setEnabled(False)
        apply_line_icon(
            self.details_button,
            "eye",
            "#FFFFFF",
            disabled_color="#94A3B8",
            accessible_name="View selected appointment details",
        )

        filters.addWidget(status_label, 1, 0)
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
            ["Date", "Time", "Doctor", "Specialty", "Clinic", "Reason", "Status"],
            stretch_column=5,
            column_widths={0: 112, 1: 120, 2: 170, 3: 150, 4: 190, 6: 132},
        )
        self.table.setItemDelegateForColumn(6, StatusBadgeDelegate(self.table))

        self.empty_state = EmptyState(
            "No appointments found",
            "Try changing the search text or status filter, then refresh the list.",
            icon="calendar",
            action_text="Refresh results",
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
        if self.status.currentText() != "All":
            params["status"] = self.status.currentText()

        # A prior empty result must not masquerade as the current loading or
        # error state. Existing rows remain visible but cannot be activated.
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
            loading_text="Loading appointments...",
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
        self.pagination.set_page(
            self._page,
            int(page.get("total_pages", 0)),
            total,
        )
        noun = "appointment" if total == 1 else "appointments"
        self.header.set_subtitle(f"{total:,} {noun} found")
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
        self.search.clear()
        was_blocked = self.status.blockSignals(True)
        try:
            self.status.setCurrentIndex(0)
        finally:
            self.status.blockSignals(was_blocked)
        self.model.removeRows(0, self.model.rowCount())
        self.table.clearSelection()
        self.pagination.reset()
        self.header.set_subtitle(self._DEFAULT_SUBTITLE)
        self.content_stack.setCurrentWidget(self.table)
        self.details_button.setEnabled(False)
