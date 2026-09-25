"""Invoice Management and Creation View for Clinic Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
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
from frontend.widgets.status_badge import StatusBadge


class InvoiceManagementView(BaseApiView):
    """View to manage all clinic billing, issue invoices for post-exam appointments, and trigger payments."""

    pay_invoice_requested = Signal(int)  # invoice_id

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._current_page = 1
        self._page_size = 15

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self.header = PageHeader(
            "Hóa đơn",
            "Lập và theo dõi hóa đơn viện phí",
            action_label="Lập hóa đơn",
            parent=self,
        )
        self.header.action_clicked.connect(self._create_invoice_dialog)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Filters
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm kiếm theo tên bệnh nhân, SĐT hoặc mã HĐ...")
        self.search_input.returnPressed.connect(self._apply_filter)
        filter_bar.addWidget(self.search_input, 2)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Tất cả hóa đơn", "")
        self.status_combo.addItem("Chưa thanh toán", "UNPAID")
        self.status_combo.addItem("Đã thanh toán", "PAID")
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_bar.addWidget(self.status_combo, 1)

        self.btn_filter = QPushButton("Lọc")
        self.btn_filter.clicked.connect(self._apply_filter)
        filter_bar.addWidget(self.btn_filter)

        layout.addLayout(filter_bar)

        # Invoices Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Mã HĐ", "Mã hẹn", "Bệnh nhân", "Số điện thoại", "Bác sĩ", "Tổng tiền", "Trạng thái", "Thao tác"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.empty_state = EmptyState(
            "Không tìm thấy hóa đơn",
            "Hóa đơn viện phí được lập sẽ hiển thị tại danh sách này.",
            parent=self,
        )
        layout.addWidget(self.empty_state)
        self.empty_state.hide()

        self.pagination = Pagination(parent=self)
        self.pagination.page_requested.connect(self._go_to_page)
        layout.addWidget(self.pagination)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.load_invoices()

    def _apply_filter(self) -> None:
        self._current_page = 1
        self.load_invoices()

    def _go_to_page(self, page: int) -> None:
        self._current_page = page
        self.load_invoices()

    def load_invoices(self) -> None:
        status_param = self.status_combo.currentData() or None
        keyword_param = self.search_input.text().strip() or None

        params = {
            "page": self._current_page,
            "page_size": self._page_size,
        }
        if status_param:
            params["status"] = status_param
        if keyword_param:
            params["keyword"] = keyword_param

        self.run_api_task(
            "load_invoices",
            lambda: self.api_client.get("/api/v1/reception/invoices", params=params),
            self._on_invoices_loaded,
            loading_text="Đang tải hóa đơn...",
        )

    def _on_invoices_loaded(self, data: dict[str, Any]) -> None:
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

        for row, inv in enumerate(items):
            inv_id = inv.get("invoice_id", 0)
            appt_id = inv.get("appointment_id", 0)
            patient_name = inv.get("patient_name", "")
            patient_phone = inv.get("patient_phone", "") or "—"
            doctor_name = inv.get("doctor_name", "")
            amount_val = inv.get("total_amount", 0)
            status = inv.get("status", "UNPAID")

            self.table.setItem(row, 0, QTableWidgetItem(f"INV-{inv_id:04d}"))
            self.table.setItem(row, 1, QTableWidgetItem(f"#{appt_id}"))
            self.table.setItem(row, 2, QTableWidgetItem(patient_name))
            self.table.setItem(row, 3, QTableWidgetItem(patient_phone))
            self.table.setItem(row, 4, QTableWidgetItem(doctor_name))
            self.table.setItem(row, 5, QTableWidgetItem(f"{float(amount_val):,.0f} ₫"))

            badge = StatusBadge(status)
            self.table.setCellWidget(row, 6, badge)

            if status == "UNPAID":
                btn_pay = QPushButton("Thu phí")
                btn_pay.setStyleSheet("background-color: #15803d; color: white; border-radius: 6px; padding: 4px 10px; font-weight: 600; font-size: 11px;")
                btn_pay.clicked.connect(lambda _, i_id=inv_id: self.pay_invoice_requested.emit(i_id))
                self.table.setCellWidget(row, 7, btn_pay)
            else:
                method = "Tiền mặt" if inv.get('payment_method') == "CASH" else "Thẻ"
                paid_label = QLabel(f"Đã thu ({method})")
                paid_label.setStyleSheet("color: #166534; font-size: 11px; font-weight: 600; padding: 4px;")
                self.table.setCellWidget(row, 7, paid_label)

    def _create_invoice_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Lập hóa đơn")
        dialog.resize(480, 420)
        d_layout = QVBoxLayout(dialog)

        form = QFormLayout()
        appt_input = QLineEdit()
        form.addRow("Mã lịch hẹn (*):", appt_input)
        d_layout.addLayout(form)

        items_label = QLabel("Chi tiết dịch vụ:")
        items_label.setStyleSheet("font-weight: 700; margin-top: 10px;")
        d_layout.addWidget(items_label)

        # Simple pre-defined line items for quick billing
        item_table = QTableWidget()
        item_table.setColumnCount(3)
        item_table.setHorizontalHeaderLabels(["Tên dịch vụ / Thuốc", "Số lượng", "Đơn giá (₫)"])
        item_table.setRowCount(3)

        default_items = [
            ("Khám chuyên khoa", 1, 200000),
            ("Xét nghiệm chỉ định", 1, 150000),
            ("Thuốc điều trị", 1, 100000),
        ]

        for i, (name, qty, price) in enumerate(default_items):
            item_table.setItem(i, 0, QTableWidgetItem(name))
            item_table.setItem(i, 1, QTableWidgetItem(str(qty)))
            item_table.setItem(i, 2, QTableWidgetItem(str(price)))

        item_table.horizontalHeader().setStretchLastSection(True)
        d_layout.addWidget(item_table)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(dialog.reject)
        btn_submit = QPushButton("Tạo hóa đơn")
        btn_submit.setStyleSheet("background-color: #0f766e; color: white; font-weight: bold; padding: 8px 16px;")
        btn_submit.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_submit)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            appt_id_text = appt_input.text().strip()
            if not appt_id_text.isdigit():
                self.feedback.show_message("Sai thông tin", "Vui lòng nhập mã lịch hẹn hợp lệ dạng số.", severity="danger")
                return

            items_payload = []
            for r in range(item_table.rowCount()):
                name_cell = item_table.item(r, 0)
                qty_cell = item_table.item(r, 1)
                price_cell = item_table.item(r, 2)
                if name_cell and qty_cell and price_cell:
                    items_payload.append({
                        "item_name": name_cell.text().strip(),
                        "quantity": int(qty_cell.text().strip() or "1"),
                        "unit_price": float(price_cell.text().strip() or "0"),
                    })

            if not items_payload:
                self.feedback.show_message("Thiếu dịch vụ", "Vui lòng thêm ít nhất một khoản mục dịch vụ.", severity="danger")
                return

            payload = {
                "appointment_id": int(appt_id_text),
                "items": items_payload,
            }

            self.run_api_task(
                "create_invoice",
                lambda: self.api_client.post("/api/v1/reception/invoices", json=payload),
                lambda res: self._on_invoice_created(res),
                loading_text="Đang lập hóa đơn...",
            )

    def _on_invoice_created(self, inv: dict[str, Any]) -> None:
        inv_id = inv.get("invoice_id", 0)
        total = float(inv.get("total_amount", 0))
        self.feedback.show_message(
            "Lập hóa đơn thành công",
            f"Đã lập hóa đơn INV-{inv_id:04d} với số tiền {total:,.0f} ₫.",
            severity="success",
        )
        self.load_invoices()
