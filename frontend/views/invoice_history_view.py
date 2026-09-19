"""Paginated patient invoice history."""

from __future__ import annotations

from PySide6.QtCore import QModelIndex, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
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
    format_money,
    require_page,
    status_item,
    table_item,
)
from frontend.widgets.pagination import PaginationWidget


class InvoiceHistoryView(BaseApiView):
    invoice_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        title = QLabel("Invoice History")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        controls = QHBoxLayout()
        controls.addStretch()
        controls.addWidget(QLabel("Status"))
        self.status = QComboBox()
        self.status.addItems(["All", "PAID", "UNPAID"])
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setObjectName("secondaryButton")
        self.details_button = QPushButton("View Details")
        self.details_button.setObjectName("primaryButton")
        self.details_button.setEnabled(False)
        controls.addWidget(self.status)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.details_button)
        root.addLayout(controls)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.model: QStandardItemModel = configure_table(
            self.table, ["Invoice", "Date", "Total Amount", "Status"]
        )
        root.addWidget(self.table, 1)
        self.pagination = PaginationWidget()
        root.addWidget(self.pagination)

        self.status.currentIndexChanged.connect(self._filter_changed)
        self.refresh_button.clicked.connect(self.load)
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
        if self.status.currentText() != "All":
            params["status"] = self.status.currentText()
        self.run_api_task(
            "invoices",
            lambda: self.api_client.get("/api/v1/invoices/me", params=params),
            self._render,
            controls=(
                self.status,
                self.refresh_button,
                self.details_button,
                self.pagination,
            ),
            loading_text="Loading invoices…",
            on_finished=self._sync_details_button,
        )

    def _render(self, payload: object) -> None:
        page = require_page(payload)
        self.model.removeRows(0, self.model.rowCount())
        for invoice in page["items"]:
            invoice_id = int(invoice["invoice_id"])
            self.model.appendRow(
                [
                    table_item(f"#INV-{invoice_id:06d}", user_data=invoice_id),
                    table_item(format_datetime(invoice.get("created_at"))),
                    table_item(format_money(invoice.get("total_amount"))),
                    status_item(invoice.get("status")),
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
        invoice_id = self._selected_id()
        if invoice_id is not None:
            self.invoice_requested.emit(invoice_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=0x0100)
        if value is not None:
            self.invoice_requested.emit(int(value))

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
        was_blocked = self.status.blockSignals(True)
        try:
            self.status.setCurrentIndex(0)
        finally:
            self.status.blockSignals(was_blocked)
        self.model.removeRows(0, self.model.rowCount())
        self.pagination.reset()
        self.details_button.setEnabled(False)
