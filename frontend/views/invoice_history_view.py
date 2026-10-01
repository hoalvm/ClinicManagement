"""Paginated patient invoice history."""

from __future__ import annotations

from PySide6.QtCore import QDate, QModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QCalendarWidget,
    QCheckBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import (
    BaseApiView,
    configure_table,
    format_datetime,
    format_money,
    require_page,
    table_item,
)
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import PaginationWidget
from frontend.widgets.state_host import StateHost
from frontend.widgets.status_badge import StatusBadgeDelegate


class InvoiceHistoryView(BaseApiView):
    invoice_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._page = 1
        self._total_invoices = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)

        self.header = PageHeader(t("invoice_history_title"), t("invoice_history_subtitle"))
        root.addWidget(self.header)

        filter_card = QFrame()
        filter_card.setObjectName("filterBar")
        filters = QGridLayout(filter_card)
        filters.setContentsMargins(16, 16, 16, 16)
        filters.setHorizontalSpacing(10)
        filters.setVerticalSpacing(8)

        self.filter_hint = QLabel(t("filter_by_status"))
        self.filter_hint.setObjectName("mutedLabel")
        filters.addWidget(self.filter_hint, 0, 0, 1, 5)

        self.date_filter = QCheckBox(t("filter_by_appointment_date"))
        self.date_filter.setObjectName("filterCheckBox")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        self.date_edit.setEnabled(False)
        self.date_edit.calendarWidget().setMinimumSize(360, 280)
        self.date_edit.calendarWidget().setGridVisible(True)
        self.date_edit.calendarWidget().setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.date_edit.setAccessibleName(t("filter_by_appointment_date"))

        self.status_label = QLabel(t("field_payment_status"))
        self.status_label.setObjectName("fieldLabel")
        self.status = ChevronComboBox()
        self.status.setMinimumWidth(170)
        self.status.setAccessibleName(t("a11y_filter_invoices"))
        self.status.addItem(t("status_all"), "All")
        self.status.addItem(t("status_paid"), "PAID")
        self.status.addItem(t("status_unpaid"), "UNPAID")
        self.status_label.setBuddy(self.status)

        self.refresh_button = QPushButton(t("btn_refresh"))
        self.refresh_button.setObjectName("secondaryButton")
        self.refresh_button.setAccessibleName(t("btn_refresh"))
        self.details_button = QPushButton(t("btn_view_details"))
        self.details_button.setObjectName("primaryButton")
        self.details_button.setAccessibleName(t("btn_view_details"))
        self.details_button.setEnabled(False)

        filters.addWidget(self.date_filter, 1, 0)
        filters.addWidget(self.date_edit, 1, 1)
        filters.addWidget(self.status_label, 1, 2)
        filters.addWidget(self.status, 1, 3)
        filters.addWidget(self.refresh_button, 1, 4)
        filters.addWidget(self.details_button, 2, 4)
        root.addWidget(filter_card)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        self.table = QTableView()
        self.table.setAccessibleName(t("a11y_invoice_results"))
        self.table.setAccessibleDescription(t("a11y_open_selected_row"))
        self.model: QStandardItemModel = configure_table(
            self.table,
            [t("th_invoice_num"), t("field_date"), t("th_total_amount"), t("field_payment_status")],
            stretch_column=1,
            column_widths={0: 122, 2: 148, 3: 122},
        )
        self.table.setItemDelegateForColumn(3, StatusBadgeDelegate(self.table))

        self.state_host = StateHost(self.table)
        self.bind_state_host(self.state_host)
        self.empty_state = self.state_host.empty
        self.empty_state.set_title(t("no_invoices_found"))
        self.empty_state.set_description(t("no_invoices_desc"))
        self.empty_state.set_action(t("btn_refresh"))
        self.empty_state.setAccessibleName(t("no_invoices_found"))
        root.addWidget(self.state_host, 1)

        self.pagination = PaginationWidget()
        self.pagination.setAccessibleName(t("invoice_history_title"))
        root.addWidget(self.pagination)

        self.status.currentIndexChanged.connect(self._filter_changed)
        self.date_filter.toggled.connect(self._date_filter_changed)
        self.date_edit.dateChanged.connect(lambda: self._search() if self.date_filter.isChecked() else None)
        self.refresh_button.clicked.connect(self.load)
        self.details_button.clicked.connect(self._open_selected)
        self.table.activated.connect(self._open_index)
        self.table.selectionModel().selectionChanged.connect(
            lambda *_args: self._sync_details_button()
        )
        self.state_host.empty_action_requested.connect(self._retry)
        self.state_host.retry_requested.connect(self._retry)
        self.pagination.page_changed.connect(self._change_page)
        self.pagination.page_size_changed.connect(self._page_size_changed)

        get_i18n().language_changed.connect(self.retranslate_ui)

    def retranslate_ui(self) -> None:
        """Update all text in InvoiceHistoryView according to current language."""
        self.header.set_title(t("invoice_history_title"))
        if self._total_invoices > 0:
            self.header.set_subtitle(t("invoices_count", count=self._total_invoices))
        else:
            self.header.set_subtitle(t("invoice_history_subtitle"))
        self.filter_hint.setText(t("filter_by_status"))
        self.date_filter.setText(t("filter_by_appointment_date"))
        self.date_edit.setAccessibleName(t("filter_by_appointment_date"))
        self.status_label.setText(t("field_payment_status"))

        curr_data = self.status.currentData()
        self.status.blockSignals(True)
        self.status.clear()
        self.status.addItem(t("status_all"), "All")
        self.status.addItem(t("status_paid"), "PAID")
        self.status.addItem(t("status_unpaid"), "UNPAID")
        idx = self.status.findData(curr_data)
        if idx >= 0:
            self.status.setCurrentIndex(idx)
        self.status.blockSignals(False)

        self.refresh_button.setText(t("btn_refresh"))
        self.details_button.setText(t("btn_view_details"))
        self.status.setAccessibleName(t("a11y_filter_invoices"))
        self.refresh_button.setAccessibleName(t("btn_refresh"))
        self.details_button.setAccessibleName(t("btn_view_details"))
        self.table.setAccessibleName(t("a11y_invoice_results"))
        self.table.setAccessibleDescription(t("a11y_open_selected_row"))
        self.empty_state.setAccessibleName(t("no_invoices_found"))
        self.pagination.setAccessibleName(t("invoice_history_title"))
        self.empty_state.set_title(t("no_invoices_found"))
        self.empty_state.set_description(t("no_invoices_desc"))
        self.empty_state.set_action(t("btn_refresh"))
        headers = [t("th_invoice_num"), t("field_date"), t("th_total_amount"), t("field_payment_status")]
        for col, h in enumerate(headers):
            self.model.setHeaderData(col, Qt.Orientation.Horizontal, h)

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        params: dict[str, object] = {
            "page": self._page,
            "page_size": self.pagination.page_size,
        }
        status_val = self.status.currentData() or "All"
        if status_val != "All":
            params["status"] = status_val
        if self.date_filter.isChecked():
            params["appointment_date"] = self.date_edit.date().toString("yyyy-MM-dd")

        self.details_button.setEnabled(False)
        self.run_api_task(
            "invoices",
            lambda: self.api_client.get("/api/v1/invoices/me", params=params),
            self._render,
            controls=(
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
        for invoice in items:
            invoice_id = int(invoice["invoice_id"])
            amount_item = table_item(format_money(invoice.get("total_amount")))
            amount_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            self.model.appendRow(
                [
                    table_item(f"#INV-{invoice_id:06d}", user_data=invoice_id),
                    table_item(format_datetime(invoice.get("created_at"))),
                    amount_item,
                    table_item(invoice.get("status")),
                ]
            )

        self._page = int(page.get("page", self._page))
        total = int(page.get("total", 0))
        self._total_invoices = total
        self.pagination.set_page(
            self._page,
            int(page.get("total_pages", 0)),
            total,
        )
        self.header.set_subtitle(t("invoices_count", count=total))
        self.table.clearSelection()
        self.details_button.setEnabled(False)
        if items:
            self.state_host.show_content()
        else:
            self.state_host.show_empty(
                t("no_invoices_found"),
                t("no_invoices_desc"),
                action_text=t("btn_refresh"),
            )

    def _selected_id(self) -> int | None:
        indexes = self.table.selectionModel().selectedRows(0)
        if not indexes:
            return None
        value = indexes[0].data(role=Qt.ItemDataRole.UserRole)
        return int(value) if value is not None else None

    def _open_selected(self) -> None:
        invoice_id = self._selected_id()
        if invoice_id is not None:
            self.invoice_requested.emit(invoice_id)

    def _open_index(self, index: QModelIndex) -> None:
        value = self.model.index(index.row(), 0).data(role=Qt.ItemDataRole.UserRole)
        if value is not None:
            self.invoice_requested.emit(int(value))

    def _filter_changed(self, _index: int = 0) -> None:
        self._page = 1
        self.load()

    def _date_filter_changed(self, enabled: bool) -> None:
        self.date_edit.setEnabled(enabled)
        self._search()

    def _retry(self) -> None:
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
        self._total_invoices = 0
        was_blocked = self.status.blockSignals(True)
        try:
            self.status.setCurrentIndex(0)
            self.date_filter.setChecked(False)
            self.date_edit.setDate(QDate.currentDate())
        finally:
            self.status.blockSignals(was_blocked)
        self.model.removeRows(0, self.model.rowCount())
        self.table.clearSelection()
        self.pagination.reset()
        self.header.set_subtitle(t("invoice_history_subtitle"))
        self.state_host.show_content()
        self.details_button.setEnabled(False)
