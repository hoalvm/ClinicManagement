"""Paginated appointment history."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import (
    BaseApiView,
    configure_table,
    format_date,
    format_time,
    require_page,
    status_item,
    table_item,
)
from frontend.widgets.pagination import PaginationWidget


class AppointmentHistoryView(BaseApiView):
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        title = QLabel("Appointment History")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search doctor, specialty, clinic, or reason")
        self.search.setClearButtonEnabled(True)
        self.status = QComboBox()
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
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.details_button = QPushButton("View Details")
        self.details_button.setObjectName("primaryButton")
        self.details_button.setEnabled(False)
        controls.addWidget(self.search, 1)
        controls.addWidget(self.status)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.details_button)
        root.addLayout(controls)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.model: QStandardItemModel = configure_table(
            self.table,
            ["Date", "Time", "Doctor", "Specialty", "Clinic", "Reason", "Status"],
        )
        root.addWidget(self.table, 1)
        self.pagination = PaginationWidget()
        root.addWidget(self.pagination)

        self.search.returnPressed.connect(self._search)
        self.status.currentIndexChanged.connect(self._filter_changed)
        self.refresh_button.clicked.connect(self._search)
        self.details_button.clicked.connect(self._open_selected)
        self.table.doubleClicked.connect(self._open_index)
        self.table.selectionModel().selectionChanged.connect(
            lambda: self.details_button.setEnabled(bool(self.table.selectionModel().selectedRows()))
        )
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
        self.run_api_task(
            "appointments",
            lambda: self.api_client.get("/api/v1/appointments/me", params=params),
            self._render,
            controls=(
                self.search,
                self.status,
                self.refresh_button,
                self.details_button,
                self.pagination,
            ),
            loading_text="Loading appointments…",
            on_finished=self._sync_details_button,
        )

    def _render(self, payload: object) -> None:
        page = require_page(payload)
        self.model.removeRows(0, self.model.rowCount())
        for appointment in page["items"]:
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
                    status_item(appointment.get("status")),
                ]
            )
        self._page = int(page.get("page", self._page))
        self.pagination.set_page(
            self._page,
            int(page.get("total_pages", 0)),
            int(page.get("total", 0)),
        )
        self.details_button.setEnabled(False)

    def _selected_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows(0)
        if not indexes:
            return None
        value = indexes[0].data(role=0x0100)
        return int(value) if value is not None else None

    def _open_selected(self) -> None:
        appointment_id = self._selected_id()
        if appointment_id is not None:
            self.appointment_requested.emit(appointment_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=0x0100)
        if value is not None:
            self.appointment_requested.emit(int(value))

    def _search(self) -> None:
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
        self.details_button.setEnabled(bool(self.table.selectionModel().selectedRows()))

    def clear_data(self) -> None:
        self._page = 1
        self.search.clear()
        was_blocked = self.status.blockSignals(True)
        try:
            self.status.setCurrentIndex(0)
        finally:
            self.status.blockSignals(was_blocked)
        self.model.removeRows(0, self.model.rowCount())
        self.pagination.reset()
        self.details_button.setEnabled(False)
