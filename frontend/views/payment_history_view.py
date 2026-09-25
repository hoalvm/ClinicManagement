"""Payment History View for Clinic Cashier and Accountants."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.views.common import BaseApiView
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination


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
        self.search_input.returnPressed.connect(self._apply_filter)
        filter_bar.addWidget(self.search_input, 2)

        self.method_combo = QComboBox()
        self.method_combo.addItem("Tất cả phương thức", None)
        self.method_combo.addItem("Tiền mặt", "CASH")
        self.method_combo.addItem("Thẻ ngân hàng", "CARD")
        self.method_combo.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.method_combo, 1)

        self.btn_filter = QPushButton("Lọc")
        self.btn_filter.clicked.connect(self._apply_filter)
        filter_bar.addWidget(self.btn_filter)

        layout.addWidget(filter_card)

        # Payments Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Mã GD", "Mã HĐ", "Bệnh nhân", "Bác sĩ", "Số tiền", "Phương thức", "Thời gian"
        ])
        hdr = self.table.horizontalHeader()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        self.empty_state = EmptyState(
            "Chưa có dữ liệu thanh toán",
            "Các giao dịch thanh toán đã hoàn tất sẽ hiển thị tại đây.",
            parent=self,
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

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
            loading_text="Đang tải dữ liệu thu phí...",
        )

    def _on_payments_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        total = data.get("total", 0)
        total_pages = data.get("total_pages", 1)
        self.pagination.update_state(self._current_page, total_pages, total)

        if not items:
            self.table.hide()
            self.empty_state.show()
            return

        self.empty_state.hide()
        self.table.show()
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            p_id = item.get("payment_id", 0)
            inv_id = item.get("invoice_id", 0)
            patient_name = item.get("patient_name", "")
            doctor_name = item.get("doctor_name", "")
            amount = float(item.get("amount", 0))
            method = item.get("payment_method", "CASH")
            dt = str(item.get("payment_date", ""))[:19].replace("T", " ")

            id_item = QTableWidgetItem(f"TXN-{p_id:04d}")
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, id_item)

            inv_item = QTableWidgetItem(f"INV-{inv_id:04d}")
            inv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 1, inv_item)

            self.table.setItem(row, 2, QTableWidgetItem(patient_name))
            self.table.setItem(row, 3, QTableWidgetItem(doctor_name))

            amount_item = QTableWidgetItem(f"{amount:,.0f} ₫")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 4, amount_item)

            method_label = "Tiền mặt" if method == "CASH" else ("Thẻ" if method == "CARD" else method)
            method_item = QTableWidgetItem(method_label)
            method_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 5, method_item)

            self.table.setItem(row, 6, QTableWidgetItem(dt))
            self.table.setRowHeight(row, 40)
