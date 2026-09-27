"""Payment History View for Clinic Cashier and Accountants."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import ColumnPriority, ColumnSpec
from frontend.views.common import BaseApiView, format_datetime, format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost


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
            "Lịch sử thu phí",
            "Nhật ký giao dịch thanh toán viện phí",
            action_label="Làm mới",
            parent=self,
        )
        self.header.action_clicked.connect(self.load_payments)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Filters
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_bar = QHBoxLayout(filter_card)
        filter_bar.setContentsMargins(16, 10, 16, 10)
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm theo tên bệnh nhân, SĐT hoặc mã HĐ...")
        self.search_input.setAccessibleName("Tìm kiếm lịch sử thu phí")
        self.search_input.returnPressed.connect(self._apply_filter)
        filter_bar.addWidget(self.search_input, 2)

        self.method_combo = QComboBox()
        self.method_combo.addItem("Tất cả phương thức", None)
        self.method_combo.addItem("Tiền mặt", "CASH")
        self.method_combo.addItem("Thẻ ngân hàng", "CARD")
        self.method_combo.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.method_combo, 1)

        self.btn_filter = QPushButton("Lọc")
        self.btn_filter.setCursor(Qt.PointingHandCursor)
        self.btn_filter.clicked.connect(self._apply_filter)
        filter_bar.addWidget(self.btn_filter)

        layout.addWidget(filter_card)

        # Payments Table
        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Mã GD",
                    "payment_id",
                    minimum_width=82,
                    preferred_width=92,
                    priority=ColumnPriority.CRITICAL,
                    formatter=lambda value: f"TXN-{int(value or 0):04d}",
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Mã HĐ",
                    "invoice_id",
                    minimum_width=78,
                    preferred_width=88,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: f"INV-{int(value or 0):04d}",
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient_name",
                    minimum_width=130,
                    stretch=True,
                    priority=ColumnPriority.CRITICAL,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=112,
                    preferred_width=140,
                    priority=ColumnPriority.NORMAL,
                ),
                ColumnSpec(
                    "Số tiền",
                    "amount",
                    minimum_width=104,
                    preferred_width=116,
                    priority=ColumnPriority.CRITICAL,
                    formatter=format_money,
                    alignment=Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter,
                ),
                ColumnSpec(
                    "Phương thức",
                    "payment_method",
                    minimum_width=96,
                    preferred_width=110,
                    formatter=lambda value: {
                        "CASH": "Tiền mặt",
                        "CARD": "Thẻ",
                    }.get(str(value), str(value or "—")),
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Thời gian",
                    "payment_date",
                    minimum_width=126,
                    preferred_width=148,
                    formatter=format_datetime,
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

    def _apply_filter(self) -> None:
        self._current_page = 1
        self.load_payments()

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

        self.table.set_rows(items)
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
