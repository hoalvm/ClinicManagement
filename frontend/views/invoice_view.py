"""Invoice Management and Creation View for Clinic Staff."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.views.common import BaseApiView, format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.page_header import PageHeader
from frontend.widgets.pagination import Pagination
from frontend.widgets.state_host import StateHost
from frontend.widgets.status_badge import display_status
from frontend.widgets.table_actions import table_action_cell


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

        self.filters = FilterToolbar(
            "Tìm tên bệnh nhân, số điện thoại hoặc mã hóa đơn",
            search_accessible_name="Tìm kiếm hóa đơn",
        )
        self.search_input = self.filters.search_input
        self.status_combo = self.filters.add_filter(
            "status",
            (
                ("Tất cả hóa đơn", ""),
                (display_status("UNPAID", "vi"), "UNPAID"),
                (display_status("PAID", "vi"), "PAID"),
            ),
            accessible_name="Lọc hóa đơn theo trạng thái",
        )
        self.btn_filter = self.filters.clear_button
        self.filters.filters_changed.connect(self._apply_filter)
        self.search_input.returnPressed.connect(self.filters.flush_search)
        layout.addWidget(self.filters)

        self.table = AdaptiveDataTable(
            [
                ColumnSpec(
                    "Mã hóa đơn",
                    "reference",
                    minimum_width=130,
                    preferred_width=140,
                    maximum_width=150,
                    priority=ColumnPriority.HIGH,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient",
                    minimum_width=120,
                    preferred_width=166,
                    maximum_width=270,
                    priority=ColumnPriority.CRITICAL,
                    grow_weight=3,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                    stretch=True,
                ),
                ColumnSpec(
                    "Bác sĩ",
                    "doctor_name",
                    minimum_width=110,
                    preferred_width=146,
                    maximum_width=230,
                    priority=ColumnPriority.NORMAL,
                    grow_weight=2,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Tổng tiền",
                    "total_amount",
                    minimum_width=120,
                    preferred_width=126,
                    maximum_width=136,
                    priority=ColumnPriority.CRITICAL,
                    formatter=format_money,
                    display_mode=ColumnDisplayMode.FULL,
                    alignment=Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter,
                ),
                ColumnSpec(
                    "Hình thức",
                    "payment_method",
                    minimum_width=110,
                    preferred_width=110,
                    maximum_width=118,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: {
                        "CASH": "Tiền mặt",
                        "CARD": "Thẻ",
                    }.get(str(value or ""), "—"),
                    display_mode=ColumnDisplayMode.ELIDE,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                ),
                ColumnSpec(
                    "Trạng thái",
                    "status",
                    minimum_width=126,
                    preferred_width=134,
                    maximum_width=144,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.FULL,
                    alignment=Qt.AlignmentFlag.AlignCenter,
                    status=True,
                ),
                ColumnSpec(
                    "Xử lý",
                    "_actions",
                    minimum_width=120,
                    preferred_width=124,
                    maximum_width=132,
                    priority=ColumnPriority.CRITICAL,
                    display_mode=ColumnDisplayMode.ELIDE,
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

    def _apply_filter(self, _values: object | None = None) -> None:
        self._current_page = 1
        self.load_invoices()

    def _clear_filters(self) -> None:
        self.filters.clear()

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
                "reference": CellValue(
                    f"INV-{int(inv.get('invoice_id') or 0):04d}",
                    f"Hẹn #{int(inv.get('appointment_id') or 0)}",
                ),
                "patient": CellValue(
                    str(inv.get("patient_name", "") or "—"),
                    str(inv.get("patient_phone", "") or "Chưa có số điện thoại"),
                ),
                "doctor_name": inv.get("doctor_name", ""),
                "total_amount": inv.get("total_amount", 0),
                "payment_method": inv.get("payment_method"),
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

            if status == "UNPAID":
                action = QPushButton("Thu phí")
                action.setObjectName("tableActionPrimary")
                action.setCursor(Qt.PointingHandCursor)
                action.setAccessibleName(f"Thu phí hóa đơn INV-{inv_id:04d}")
                action.clicked.connect(
                    lambda _, i_id=inv_id: self.pay_invoice_requested.emit(i_id)
                )
            else:
                action = QPushButton("Xem thông tin")
                action.setObjectName("tableActionSecondary")
                action.setCursor(Qt.PointingHandCursor)
                action.setAccessibleName(f"Xem hóa đơn INV-{inv_id:04d}")
                action.clicked.connect(
                    lambda _, invoice=inv: self._show_invoice_details(invoice)
                )
            action_widget = table_action_cell(
                action,
                accessible_name=f"Thao tác hóa đơn INV-{inv_id:04d}",
            )
            self.table.setIndexWidget(self.table.model().index(row, 6), action_widget)
            self.table.verticalHeader().resizeSection(row, 60)

    def _show_invoice_details(self, invoice: dict[str, Any]) -> None:
        dialog = QDialog(self)
        invoice_id = int(invoice.get("invoice_id") or 0)
        dialog.setWindowTitle(f"Hóa đơn INV-{invoice_id:04d}")
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        details = QLabel(
            "\n".join(
                (
                    f"Bệnh nhân: {invoice.get('patient_name', '—')}",
                    f"Bác sĩ: {invoice.get('doctor_name', '—')}",
                    f"Tổng tiền: {format_money(invoice.get('total_amount', 0))}",
                    "Phương thức: "
                    + {"CASH": "Tiền mặt", "CARD": "Thẻ"}.get(
                        str(invoice.get("payment_method") or ""), "Chưa ghi nhận"
                    ),
                )
            )
        )
        details.setWordWrap(True)
        layout.addWidget(details)
        close = QPushButton("Đóng")
        close.setObjectName("primaryButton")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)
        dialog.exec()

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
        form.addRow("Mã lịch hẹn *", appt_input)
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
