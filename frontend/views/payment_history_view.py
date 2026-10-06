"""Payment History View for Clinic Cashier and Accountants."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.views.common import BaseApiView, format_datetime, format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost


def _format_payment_datetime(value: object) -> CellValue:
    """Keep date and time fully readable without making the column too wide."""

    formatted = format_datetime(value)
    date_text, separator, time_text = formatted.partition(" · ")
    return CellValue(
        date_text,
        time_text if separator else None,
        tooltip=formatted,
        accessible_text=formatted,
    )


class PaymentHistoryView(BaseApiView):
    """View to review all past completed payments, transaction timestamps, and payment methods."""

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._current_page = 1
        self._page_size = 15

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = PageHeader(
            "Lịch sử thanh toán",
            "Nhật ký giao dịch thanh toán viện phí",
            action_label="Làm mới",
            parent=self,
        )
        if self.header.action_button is not None:
            self.header.action_button.setObjectName("secondaryButton")
        self.header.action_clicked.connect(self.load_payments)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        self.filters = FilterToolbar(
            "Tìm tên bệnh nhân, số điện thoại hoặc mã hóa đơn",
            search_accessible_name="Tìm kiếm lịch sử thanh toán",
        )
        self.search_input = self.filters.search_input
        self.method_combo = self.filters.add_filter(
            "payment_method",
            (
                ("Tất cả phương thức", None),
                ("Tiền mặt", "CASH"),
                ("Chuyển khoản", "TRANSFER"),
                ("Thẻ (dữ liệu cũ)", "CARD"),
            ),
            accessible_name="Lọc theo phương thức thanh toán",
        )
        self.btn_filter = self.filters.clear_button
        self.filters.filters_changed.connect(self._apply_filter)
        self.search_input.returnPressed.connect(self.filters.flush_search)
        layout.addWidget(self.filters)

        # Payments Table
        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Giao dịch",
                    "reference",
                    minimum_width=104,
                    preferred_width=116,
                    maximum_width=136,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    preserve_full=True,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient_name",
                    minimum_width=118,
                    preferred_width=180,
                    maximum_width=260,
                    grow_weight=3,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    stretch=True,
                    priority=ColumnPriority.CRITICAL,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=106,
                    preferred_width=160,
                    maximum_width=230,
                    grow_weight=2,
                    priority=ColumnPriority.NORMAL,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Số tiền",
                    "amount",
                    minimum_width=104,
                    preferred_width=116,
                    maximum_width=128,
                    priority=ColumnPriority.CRITICAL,
                    formatter=format_money,
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter,
                ),
                ColumnSpec(
                    "Phương thức",
                    "payment_method",
                    minimum_width=96,
                    preferred_width=110,
                    maximum_width=122,
                    formatter=lambda value: {
                        "CASH": "Tiền mặt",
                        "TRANSFER": "Chuyển khoản",
                        "CARD": "Thẻ",
                    }.get(str(value), str(value or "—")),
                    display_mode=ColumnDisplayMode.FULL,
                    preserve_full=True,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thời gian",
                    "payment_date",
                    minimum_width=126,
                    preferred_width=132,
                    maximum_width=148,
                    formatter=_format_payment_datetime,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    preserve_full=True,
                ),
            ],
            accessible_name="Lịch sử giao dịch thu phí",
        )
        self.table.setMinimumHeight(260)
        self.state_host = StateHost(self.table)
        self.bind_state_host(self.state_host)
        self.empty_state = self.state_host.empty
        self.empty_state.set_title("Chưa có dữ liệu thanh toán")
        self.empty_state.set_description(
            "Các giao dịch thanh toán đã hoàn tất sẽ hiển thị tại đây."
        )
        self.empty_state.set_action("Làm mới")
        self.state_host.empty_action_requested.connect(self._retry)
        self.state_host.retry_requested.connect(self._retry)
        layout.addWidget(self.state_host, 1)

        self.pagination = Pagination(parent=self)
        self.pagination.page_requested.connect(self._go_to_page)
        layout.addWidget(self.pagination)

        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.load_payments()

    def _apply_filter(self, _values: object | None = None) -> None:
        self._current_page = 1
        self.load_payments()

    def _clear_filters(self) -> None:
        self.filters.clear()

    def _go_to_page(self, page: int) -> None:
        self._current_page = page
        self.load_payments()

    def load_payments(self) -> None:
        method_param = self.method_combo.currentData()
        keyword_param = self.search_input.text().strip() or None

        params = {
            "page": self._current_page,
            "page_size": self._page_size,
        }
        if method_param:
            params["payment_method"] = method_param
        if keyword_param:
            params["keyword"] = keyword_param

        self.run_api_task(
            "load_payments",
            lambda: self.api_client.get("/api/v1/reception/payments", params=params),
            self._on_payments_loaded,
            controls=(
                self.search_input,
                self.method_combo,
                self.btn_filter,
                self.pagination,
            ),
            loading_text="Đang tải dữ liệu thu phí...",
        )

    def _on_payments_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        total = data.get("total", 0)
        total_pages = data.get("total_pages", 1)
        self.pagination.update_state(self._current_page, total_pages, total)

        rows = [
            {
                **payment,
                "reference": CellValue(
                    f"TXN-{int(payment.get('payment_id') or 0):04d}",
                    f"INV-{int(payment.get('invoice_id') or 0):04d}",
                ),
            }
            for payment in items
        ]
        self.table.set_rows(rows)
        if items:
            self.state_host.show_content()
        else:
            self.state_host.show_empty(
                "Chưa có dữ liệu thanh toán",
                "Các giao dịch thanh toán đã hoàn tất sẽ hiển thị tại đây.",
                action_text="Làm mới",
            )

    def _retry(self) -> None:
        self.load_payments()
