"""Invoice Management and Creation View for Clinic Staff."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.design_system import ColumnPriority, ColumnSpec
from frontend.views.common import BaseApiView, format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost


class InvoiceManagementView(BaseApiView):
    """View to manage all clinic billing, issue invoices for post-exam appointments, and trigger payments."""

    pay_invoice_requested = Signal(int)  # invoice_id

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
        filter_card = QFrame()
        filter_card.setObjectName("filterCard")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 10, 16, 10)
        filter_layout.setSpacing(12)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tìm theo tên bệnh nhân, SĐT hoặc mã HĐ...")
        self.search_input.setAccessibleName("Tìm kiếm hóa đơn")
        self.search_input.returnPressed.connect(self._apply_filter)
        filter_layout.addWidget(self.search_input, 2)

        self.status_combo = QComboBox()
        self.status_combo.addItem("Tất cả hóa đơn", "")
        self.status_combo.addItem("Chưa thanh toán", "UNPAID")
        self.status_combo.addItem("Đã thanh toán", "PAID")
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_layout.addWidget(self.status_combo, 1)

        self.btn_filter = QPushButton("Lọc")
        self.btn_filter.setCursor(Qt.PointingHandCursor)
        self.btn_filter.clicked.connect(self._apply_filter)
        filter_layout.addWidget(self.btn_filter)

        layout.addWidget(filter_card)

        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Mã HĐ",
                    "invoice_id",
                    minimum_width=76,
                    preferred_width=84,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: f"INV-{int(value or 0):04d}",
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Mã hẹn",
                    "appointment_id",
                    minimum_width=68,
                    preferred_width=76,
                    priority=ColumnPriority.NORMAL,
                    formatter=lambda value: f"#{int(value or 0)}",
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient_name",
                    minimum_width=120,
                    priority=ColumnPriority.CRITICAL,
                    stretch=True,
                ),
                ColumnSpec(
                    "Số điện thoại",
                    "patient_phone",
                    minimum_width=96,
                    preferred_width=106,
                    priority=ColumnPriority.HIGH,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=100,
                    preferred_width=120,
                    priority=ColumnPriority.NORMAL,
                ),
                ColumnSpec(
                    "Tổng tiền",
                    "total_amount",
                    minimum_width=100,
                    preferred_width=112,
                    priority=ColumnPriority.CRITICAL,
                    formatter=format_money,
                    alignment=Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=100,
                    preferred_width=110,
                    priority=ColumnPriority.CRITICAL,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                    status=True,
                ),
                ColumnSpec(
                    "Thao tác",
                    "_actions",
                    minimum_width=112,
                    preferred_width=124,
                    priority=ColumnPriority.CRITICAL,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
            ],
            accessible_name="Danh sách hóa đơn",
        )
        self.table.setAccessibleDescription(
            "Bảng hóa đơn chỉ đọc; trạng thái và thao tác thu phí luôn hiển thị."
        )
        self.table.setMinimumHeight(260)

        self.state_host = StateHost(self.table)
        self.bind_state_host(self.state_host)
        self.empty_state = self.state_host.empty
        self.empty_state.set_title("Không tìm thấy hóa đơn")
        self.empty_state.set_description(
            "Hóa đơn viện phí được lập sẽ hiển thị tại danh sách này."
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
            controls=(
                self.search_input,
                self.status_combo,
                self.btn_filter,
                self.pagination,
            ),
            loading_text="Đang tải hóa đơn...",
        )

    def _on_invoices_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        total = data.get("total", 0)
        total_pages = data.get("total_pages", 1)
        self.pagination.update_state(self._current_page, total_pages, total)

        rows = [
            {
                "invoice_id": inv.get("invoice_id", 0),
                "appointment_id": inv.get("appointment_id", 0),
                "patient_name": inv.get("patient_name", ""),
                "patient_phone": inv.get("patient_phone", "") or "—",
                "doctor_name": inv.get("doctor_name", ""),
                "total_amount": inv.get("total_amount", 0),
                "status": inv.get("status", "UNPAID"),
                "_actions": "",
            }
            for inv in items
        ]
        self.table.set_rows(rows)

        if not items:
            self.state_host.show_empty(
                "Không tìm thấy hóa đơn",
                "Hóa đơn viện phí được lập sẽ hiển thị tại danh sách này.",
                action_text="Làm mới",
            )
            return

        self.state_host.show_content()

        for row, inv in enumerate(items):
            inv_id = inv.get("invoice_id", 0)
            status = inv.get("status", "UNPAID")

            action_widget = QWidget()
            action_widget.setObjectName("tableCellWidget")
            act_layout = QHBoxLayout(action_widget)
            act_layout.setContentsMargins(4, 0, 4, 0)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if status == "UNPAID":
                btn_pay = QPushButton("Thu phí")
                btn_pay.setObjectName("tableActionPrimary")
                btn_pay.setCursor(Qt.PointingHandCursor)
                btn_pay.setAccessibleName(f"Thu phí hóa đơn INV-{inv_id:04d}")
                btn_pay.clicked.connect(lambda _, i_id=inv_id: self.pay_invoice_requested.emit(i_id))
                act_layout.addWidget(btn_pay)
            else:
                method = "Tiền mặt" if inv.get("payment_method") == "CASH" else "Thẻ"
                paid_label = QLabel(f"Đã thu ({method})")
                paid_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                paid_label.setObjectName("paidLabel")
                act_layout.addWidget(paid_label)

            self.table.setIndexWidget(self.table.model().index(row, 7), action_widget)
            self.table.verticalHeader().resizeSection(row, 50)

    def _retry(self) -> None:
        self.load_invoices()

    @staticmethod
    def _collect_invoice_items(item_table: QTableWidget) -> list[dict[str, object]]:
        """Validate editable invoice rows before creating a request payload."""

        items: list[dict[str, object]] = []
        for row in range(item_table.rowCount()):
            cells = [item_table.item(row, column) for column in range(3)]
            values = [cell.text().strip() if cell is not None else "" for cell in cells]
            name, quantity_text, price_text = values
            if not any(values):
                continue
            if not all(values):
                raise ValueError(f"Dòng {row + 1} chưa nhập đủ tên, số lượng và đơn giá.")
            try:
                quantity = int(quantity_text)
            except ValueError as exc:
                raise ValueError(f"Số lượng ở dòng {row + 1} phải là số nguyên.") from exc
            try:
                unit_price = Decimal(price_text)
            except InvalidOperation as exc:
                raise ValueError(f"Đơn giá ở dòng {row + 1} không hợp lệ.") from exc
            if quantity <= 0:
                raise ValueError(f"Số lượng ở dòng {row + 1} phải lớn hơn 0.")
            if not unit_price.is_finite() or unit_price < 0:
                raise ValueError(f"Đơn giá ở dòng {row + 1} phải là số không âm.")
            items.append(
                {
                    "item_name": name,
                    "quantity": quantity,
                    "unit_price": float(unit_price),
                }
            )
        if not items:
            raise ValueError("Vui lòng thêm ít nhất một khoản mục dịch vụ.")
        return items

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
        items_label.setObjectName("fieldLabel")
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
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_submit = QPushButton("Tạo hóa đơn")
        btn_submit.setObjectName("primaryButton")
        btn_submit.setCursor(Qt.PointingHandCursor)
        btn_submit.clicked.connect(dialog.accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_submit)
        d_layout.addLayout(btn_row)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            appt_id_text = appt_input.text().strip()
            if not appt_id_text.isdigit():
                self.feedback.show_message("Sai thông tin", "Vui lòng nhập mã lịch hẹn hợp lệ dạng số.", severity="error")
                return

            try:
                items_payload = self._collect_invoice_items(item_table)
            except ValueError as exc:
                self.feedback.show_message("Sai thông tin", str(exc), severity="error")
                return

            payload = {
                "appointment_id": int(appt_id_text),
                "items": items_payload,
            }

            self.run_api_task(
                "create_invoice",
                lambda: self.api_client.post("/api/v1/reception/invoices", json=payload),
                lambda res: self._on_invoice_created(res),
                controls=(self.header.action_button,),
                loading_text="Đang lập hóa đơn...",
            )

    def _on_invoice_created(self, inv: dict[str, Any]) -> None:
        inv_id = inv.get("invoice_id", 0)
        total = float(inv.get("total_amount", 0))
        self.feedback.show_message(
            "Lập hóa đơn thành công",
            f"Đã lập hóa đơn INV-{inv_id:04d} với số tiền {format_money(total)}.",
            severity="success",
        )
        self.load_invoices()
