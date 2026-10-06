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

from frontend.api.api_client import ApiClient, ApiError
from frontend.core.config import get_frontend_settings
from frontend.ui.design_system import (
    CellValue,
    ColumnDisplayMode,
    ColumnPriority,
    ColumnSpec,
)
from frontend.views.common import BaseApiView, format_money
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.async_task_controller import AsyncTaskController
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
                    minimum_width=100,
                    preferred_width=140,
                    maximum_width=150,
                    priority=ColumnPriority.HIGH,
                    display_mode=ColumnDisplayMode.WRAP_2,
                    line_limit=2,
                ),
                ColumnSpec(
                    "Bệnh nhân",
                    "patient",
                    minimum_width=104,
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
                    minimum_width=92,
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
                    alignment=Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                ),
                ColumnSpec(
                    "Hình thức",
                    "payment_method",
                    minimum_width=88,
                    preferred_width=110,
                    maximum_width=118,
                    priority=ColumnPriority.HIGH,
                    formatter=lambda value: {
                        "CASH": "Tiền mặt",
                        "TRANSFER": "Chuyển khoản",
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
                    minimum_width=104,
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
        self.empty_state.set_description("Hóa đơn viện phí được lập sẽ hiển thị tại danh sách này.")
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

    def load_invoices(self, *, clear_feedback: bool = True) -> None:
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
            clear_feedback=clear_feedback,
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
                action.clicked.connect(lambda _, i_id=inv_id: self.pay_invoice_requested.emit(i_id))
            else:
                action = QPushButton("Xem thông tin")
                action.setObjectName("tableActionSecondary")
                action.setCursor(Qt.PointingHandCursor)
                action.setAccessibleName(f"Xem hóa đơn INV-{inv_id:04d}")
                action.clicked.connect(lambda _, invoice=inv: self._show_invoice_details(invoice))
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
                    + {"CASH": "Tiền mặt", "TRANSFER": "Chuyển khoản", "CARD": "Thẻ"}.get(
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
            if not unit_price.is_finite() or unit_price < 0 or unit_price.as_tuple().exponent < -2:
                raise ValueError(f"Đơn giá ở dòng {row + 1} phải là số không âm.")
            items.append(
                {
                    "item_name": name,
                    "quantity": quantity,
                    "unit_price": str(unit_price),
                }
            )
        if not items:
            raise ValueError("Vui lòng thêm ít nhất một khoản mục dịch vụ.")
        return items

    def _create_invoice_dialog(self) -> None:
        if get_frontend_settings().app_mode == "production":
            self._create_production_invoice_dialog()
            return
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
        help_label = QLabel("Chỉ thêm phí khám, thuốc hoặc dịch vụ thực sự thuộc ca đã hoàn tất.")
        help_label.setWordWrap(True)
        help_label.setObjectName("helperText")
        d_layout.addWidget(help_label)

        # Editable line items with explicit add/remove controls and a live total.
        item_table = QTableWidget()
        item_table.setColumnCount(4)
        item_table.setHorizontalHeaderLabels(
            ["Tên dịch vụ / Thuốc", "Số lượng", "Đơn giá (₫)", "Xóa"]
        )
        item_table.setRowCount(1)
        item_table.setItem(0, 0, QTableWidgetItem(""))
        item_table.setItem(0, 1, QTableWidgetItem("1"))
        item_table.setItem(0, 2, QTableWidgetItem("0"))

        item_table.horizontalHeader().setStretchLastSection(True)
        d_layout.addWidget(item_table)

        item_actions = QHBoxLayout()
        btn_add_item = QPushButton("Thêm khoản mục")
        btn_add_item.setObjectName("secondaryButton")
        item_actions.addWidget(btn_add_item)
        item_actions.addStretch(1)
        total_label = QLabel("Tổng cộng: 0 ₫")
        total_label.setObjectName("sectionTitle")
        item_actions.addWidget(total_label)
        d_layout.addLayout(item_actions)

        def update_total() -> None:
            total = Decimal("0")
            for row in range(item_table.rowCount()):
                quantity_item = item_table.item(row, 1)
                price_item = item_table.item(row, 2)
                try:
                    quantity = Decimal(quantity_item.text().strip()) if quantity_item else 0
                    price = Decimal(price_item.text().strip()) if price_item else 0
                    if quantity > 0 and price >= 0:
                        total += quantity * price
                except InvalidOperation:
                    continue
            total_label.setText(f"Tổng cộng: {format_money(total)}")

        def remove_item(button: QPushButton) -> None:
            for row in range(item_table.rowCount()):
                if item_table.cellWidget(row, 3) is button:
                    item_table.removeRow(row)
                    break
            if item_table.rowCount() == 0:
                add_item()
            update_total()

        def install_remove_button(row: int) -> None:
            button = QPushButton("Xóa")
            button.setObjectName("tableActionDanger")
            button.setAccessibleName(f"Xóa khoản mục dòng {row + 1}")
            button.clicked.connect(lambda _checked=False, target=button: remove_item(target))
            item_table.setCellWidget(row, 3, button)

        def add_item() -> None:
            row = item_table.rowCount()
            item_table.insertRow(row)
            item_table.setItem(row, 0, QTableWidgetItem(""))
            item_table.setItem(row, 1, QTableWidgetItem("1"))
            item_table.setItem(row, 2, QTableWidgetItem("0"))
            install_remove_button(row)
            item_table.setCurrentCell(row, 0)
            item_table.editItem(item_table.item(row, 0))
            update_total()

        for row in range(item_table.rowCount()):
            install_remove_button(row)
        item_table.itemChanged.connect(lambda _item: update_total())
        btn_add_item.clicked.connect(add_item)
        update_total()

        btn_row = QHBoxLayout()
        error_label = QLabel()
        error_label.setObjectName("errorText")
        error_label.setWordWrap(True)
        error_label.hide()
        d_layout.addWidget(error_label)
        tasks = AsyncTaskController(dialog)
        dialog.finished.connect(lambda _result: tasks.invalidate())
        btn_cancel = QPushButton("Hủy")
        btn_cancel.setObjectName("secondaryButton")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.clicked.connect(dialog.reject)
        btn_submit = QPushButton("Tạo hóa đơn")
        btn_submit.setObjectName("primaryButton")
        btn_submit.setCursor(Qt.PointingHandCursor)
        def submit() -> None:
            appt_id_text = appt_input.text().strip()
            if not appt_id_text.isdigit() or int(appt_id_text) <= 0:
                error_label.setText("Vui lòng nhập mã lịch hẹn hợp lệ dạng số.")
                error_label.show()
                return
            try:
                items_payload = self._collect_invoice_items(item_table)
            except ValueError as exc:
                error_label.setText(str(exc))
                error_label.show()
                return
            error_label.hide()
            payload = {"appointment_id": int(appt_id_text), "items": items_payload}

            def succeeded(result: dict[str, Any]) -> None:
                dialog.accept()
                self._on_invoice_created(result)

            def failed(error: Exception) -> None:
                if isinstance(error, ApiError) and error.status_code == 401:
                    dialog.reject()
                    self.session_expired.emit()
                    return
                error_label.setText(
                    error.message if isinstance(error, ApiError) else "Không thể lập hóa đơn. Vui lòng thử lại."
                )
                error_label.show()

            tasks.run(
                "create_invoice",
                lambda: self.api_client.post("/api/v1/reception/invoices", json=payload),
                succeeded,
                failed,
                controls=(btn_submit, btn_cancel, appt_input, item_table),
            )

        btn_submit.clicked.connect(submit)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_submit)
        d_layout.addLayout(btn_row)

        dialog.exec()

    def _create_production_invoice_dialog(self) -> None:
        """Review the server-owned consultation charge before issuing an invoice."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Lập hóa đơn khám")
        dialog.resize(520, 320)
        layout = QVBoxLayout(dialog)
        help_label = QLabel(
            "Hóa đơn chỉ gồm phí khám đã cấu hình. Đơn thuốc chưa được phát và không được thu trong luồng này."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        appt_input = QLineEdit()
        appt_input.setPlaceholderText("Mã lịch khám đã hoàn tất")
        appt_input.setAccessibleName("Mã lịch khám đã hoàn tất")
        layout.addWidget(appt_input)
        preview_label = QLabel("Nhập mã lịch khám và chọn Kiểm tra.")
        preview_label.setWordWrap(True)
        layout.addWidget(preview_label)
        error_label = QLabel()
        error_label.setWordWrap(True)
        error_label.setObjectName("errorText")
        error_label.hide()
        layout.addWidget(error_label)

        actions = QHBoxLayout()
        btn_check = QPushButton("Kiểm tra phí khám")
        btn_check.setObjectName("secondaryButton")
        actions.addWidget(btn_check)
        actions.addStretch(1)
        btn_cancel = QPushButton("Hủy")
        btn_cancel.clicked.connect(dialog.reject)
        actions.addWidget(btn_cancel)
        btn_create = QPushButton("Xác nhận lập hóa đơn")
        btn_create.setObjectName("primaryButton")
        btn_create.setEnabled(False)
        actions.addWidget(btn_create)
        layout.addLayout(actions)

        tasks = AsyncTaskController(dialog)
        dialog.finished.connect(lambda _result: tasks.invalidate())
        verified_id: int | None = None

        def reset_preview(_text: str) -> None:
            nonlocal verified_id
            verified_id = None
            btn_create.setEnabled(False)
            preview_label.setText("Nhập mã lịch khám và chọn Kiểm tra.")
            error_label.hide()

        appt_input.textChanged.connect(reset_preview)

        def check() -> None:
            nonlocal verified_id
            raw = appt_input.text().strip()
            if not raw.isdigit() or int(raw) <= 0:
                error_label.setText("Mã lịch khám phải là số dương.")
                error_label.show()
                return
            requested_id = int(raw)
            error_label.hide()

            def succeeded(result: dict[str, Any]) -> None:
                nonlocal verified_id
                if appt_input.text().strip() != str(requested_id):
                    return
                verified_id = requested_id
                preview_label.setText(
                    f"Bệnh nhân: {result['patient_name']}\n"
                    f"Bác sĩ: {result['doctor_name']}\n"
                    f"Khoản thu: {result['charge_name']}\n"
                    f"Tổng tiền: {format_money(Decimal(str(result['total_amount'])))}\n"
                    f"{result.get('medication_note', '')}"
                )
                btn_create.setEnabled(True)

            def failed(error: Exception) -> None:
                error_label.setText(
                    error.message if isinstance(error, ApiError)
                    else "Không thể kiểm tra phí khám. Vui lòng thử lại."
                )
                error_label.show()

            tasks.run(
                "invoice_preview",
                lambda: self.api_client.get(
                    f"/api/v1/reception/appointments/{requested_id}/invoice-preview"
                ),
                succeeded,
                failed,
                controls=(btn_check, appt_input),
            )

        def create() -> None:
            if verified_id is None or appt_input.text().strip() != str(verified_id):
                return
            error_label.hide()

            def succeeded(result: dict[str, Any]) -> None:
                dialog.accept()
                self._on_invoice_created(result)

            def failed(error: Exception) -> None:
                error_label.setText(
                    error.message if isinstance(error, ApiError)
                    else "Không thể lập hóa đơn. Vui lòng thử lại."
                )
                error_label.show()

            tasks.run(
                "create_invoice",
                lambda: self.api_client.post(
                    "/api/v1/reception/invoices", json={"appointment_id": verified_id}
                ),
                succeeded,
                failed,
                controls=(btn_create, btn_cancel, appt_input),
            )

        btn_check.clicked.connect(check)
        appt_input.returnPressed.connect(check)
        btn_create.clicked.connect(create)
        dialog.exec()

    def _on_invoice_created(self, inv: dict[str, Any]) -> None:
        inv_id = inv.get("invoice_id", 0)
        total = float(inv.get("total_amount", 0))
        self.feedback.show_message(
            "Lập hóa đơn thành công",
            f"Đã lập hóa đơn INV-{inv_id:04d} với số tiền {format_money(total)}.",
            severity="success",
        )
        self.load_invoices(clear_feedback=False)
