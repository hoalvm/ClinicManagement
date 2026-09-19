"""Paginated medical record history."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
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
    format_datetime,
    require_page,
    table_item,
)
from frontend.widgets.pagination import PaginationWidget


class MedicalHistoryView(BaseApiView):
    medical_record_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        title = QLabel("Medical History")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        controls = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search diagnosis, symptoms, doctor, or specialty")
        self.search.setClearButtonEnabled(True)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.details_button = QPushButton("View Details")
        self.details_button.setObjectName("primaryButton")
        self.details_button.setEnabled(False)
        controls.addWidget(self.search, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.details_button)
        root.addLayout(controls)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.model: QStandardItemModel = configure_table(
            self.table,
            ["Examination Date", "Doctor", "Specialty", "Diagnosis"],
        )
        root.addWidget(self.table, 1)
        self.pagination = PaginationWidget()
        root.addWidget(self.pagination)

        self.search.returnPressed.connect(self._search)
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
        self.run_api_task(
            "medical-history",
            lambda: self.api_client.get("/api/v1/medical-records/me", params=params),
            self._render,
            controls=(
                self.search,
                self.refresh_button,
                self.details_button,
                self.pagination,
            ),
            loading_text="Loading medical history…",
            on_finished=self._sync_details_button,
        )

    def _render(self, payload: object) -> None:
        page = require_page(payload)
        self.model.removeRows(0, self.model.rowCount())
        for record in page["items"]:
            doctor = record.get("doctor") or {}
            record_id = int(record["medical_record_id"])
            self.model.appendRow(
                [
                    table_item(
                        format_datetime(record.get("examination_date")),
                        user_data=record_id,
                    ),
                    table_item(doctor.get("full_name")),
                    table_item(doctor.get("specialty")),
                    table_item(record.get("diagnosis")),
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
        record_id = self._selected_id()
        if record_id is not None:
            self.medical_record_requested.emit(record_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=0x0100)
        if value is not None:
            self.medical_record_requested.emit(int(value))

    def _search(self) -> None:
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
        self.model.removeRows(0, self.model.rowCount())
        self.pagination.reset()
        self.details_button.setEnabled(False)
