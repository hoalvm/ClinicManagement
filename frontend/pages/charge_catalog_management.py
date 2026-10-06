"""Production consultation-fee versions for the administrator desktop."""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from frontend.api_client import api_client
from frontend.pages.admin_ui import AdminApiPage, AdminFormDialog, require_success
from frontend.ui.design_system import ColumnDisplayMode, ColumnPriority, ColumnSpec
from frontend.widgets.adaptive_data_table import AdaptiveDataTable
from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.page_header import PageHeader

_CODE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,49}$")
_PRICE_PATTERN = re.compile(r"^\d{1,16}(?:\.\d{1,2})?$")


def _date_text(value: object) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(str(value)).strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return "—"


def _price_text(value: object) -> str:
    try:
        amount = Decimal(str(value))
    except (ValueError, ArithmeticError):
        return "—"
    formatted = f"{amount:,.2f}"
    if formatted.endswith(".00"):
        formatted = formatted[:-3]
    return formatted.replace(",", "_").replace(".", ",").replace("_", ".") + " đ"


class ChargeCatalogManagementPage(AdminApiPage):
    """List current and retired consultation fees; create an audited price version."""

    def __init__(self) -> None:
        super().__init__()
        self._charges: list[dict] = []
        self._specialties: list[dict] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        self.header = PageHeader(
            "Bảng giá khám",
            "Mỗi chuyên khoa có một phí khám hiện hành. Tạo giá mới sẽ lưu lịch sử giá cũ.",
            action_label="Thêm phiên bản giá",
        )
        self.header.action_clicked.connect(self.open_create_dialog)
        layout.addWidget(self.header)
        self.add_request_feedback(layout)

        filters = QFrame()
        filters.setObjectName("contentCard")
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(10)
        filter_layout.addWidget(QLabel("Chuyên khoa"))
        self.specialty_filter = ChevronComboBox()
        self.specialty_filter.setAccessibleName("Lọc bảng giá theo chuyên khoa")
        self.specialty_filter.addItem("Tất cả chuyên khoa", None)
        self.specialty_filter.currentIndexChanged.connect(self._render_rows)
        filter_layout.addWidget(self.specialty_filter, 1)
        filter_layout.addWidget(QLabel("Phiên bản"))
        self.status_filter = ChevronComboBox()
        self.status_filter.setAccessibleName("Lọc phiên bản giá")
        self.status_filter.addItem("Đang hiệu lực", "active")
        self.status_filter.addItem("Lịch sử", "retired")
        self.status_filter.addItem("Tất cả", "all")
        self.status_filter.currentIndexChanged.connect(self._render_rows)
        filter_layout.addWidget(self.status_filter, 1)
        layout.addWidget(filters)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        table_card.setAccessibleName("Danh sách phiên bản phí khám")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)
        self.row_count_label = QLabel()
        self.row_count_label.setObjectName("mutedLabel")
        card_layout.addWidget(self.row_count_label)
        self.table = AdaptiveDataTable(
            (
                ColumnSpec("Chuyên khoa", "specialty", minimum_width=130, preferred_width=190,
                           maximum_width=290, grow_weight=2, priority=int(ColumnPriority.CRITICAL),
                           display_mode=ColumnDisplayMode.WRAP_2, line_limit=2),
                ColumnSpec("Mã giá", "code", minimum_width=95, preferred_width=130,
                           maximum_width=175),
                ColumnSpec("Khoản thu", "name", minimum_width=165, preferred_width=235,
                           maximum_width=340, grow_weight=2, display_mode=ColumnDisplayMode.WRAP_2,
                           line_limit=2),
                ColumnSpec("Giá (VND)", "price", minimum_width=110, preferred_width=130,
                           maximum_width=155, alignment=Qt.AlignmentFlag.AlignRight,
                           preserve_full=True),
                ColumnSpec("Từ ngày", "effective_from", minimum_width=125, preferred_width=155,
                           maximum_width=175),
                ColumnSpec("Trạng thái", "status", minimum_width=100, preferred_width=120,
                           maximum_width=140, status=True,
                           alignment=Qt.AlignmentFlag.AlignCenter),
            ),
            accessible_name="Danh sách phiên bản phí khám",
        )
        card_layout.addWidget(self.table)
        self.table_state = self.bind_state_host(
            table_card,
            self.load_data,
            empty_title="Chưa có phí khám",
            empty_description="Thêm phí khám đã được cơ sở duyệt trước khi lễ tân lập hóa đơn.",
            empty_action_text="Thêm phiên bản giá",
            on_empty_action=self.open_create_dialog,
        )
        layout.addWidget(self.table_state, 1)

    def load_data(self, *, clear_feedback: bool = True) -> bool:
        def fetch() -> tuple[list[dict], list[dict]]:
            charges = require_success(
                api_client.get(
                    "/api/v1/catalog/charges",
                    params={"category": "CONSULTATION", "include_retired": True},
                ),
                "Không thể tải bảng giá khám.",
            ).json()
            specialties = require_success(
                api_client.get("/specialties/"),
                "Không thể tải danh sách chuyên khoa.",
            ).json()
            if not isinstance(charges, list) or not isinstance(specialties, list):
                raise ValueError("Invalid catalog response")
            return charges, specialties

        return self.run_admin_task(
            "load-consultation-fees",
            fetch,
            self._populate,
            loading_text="Đang tải bảng giá khám…",
            clear_feedback=clear_feedback,
            stateful=True,
            empty_when=lambda result: not result[0],
        )

    def _populate(self, result: tuple[list[dict], list[dict]]) -> None:
        self._charges, self._specialties = result
        selected = self.specialty_filter.currentData()
        self.specialty_filter.blockSignals(True)
        self.specialty_filter.clear()
        self.specialty_filter.addItem("Tất cả chuyên khoa", None)
        for specialty in sorted(self._specialties, key=lambda item: str(item.get("SpecialtyName", ""))):
            self.specialty_filter.addItem(
                str(specialty.get("SpecialtyName") or "Chuyên khoa chưa đặt tên"),
                specialty.get("SpecialtyID"),
            )
        index = self.specialty_filter.findData(selected)
        self.specialty_filter.setCurrentIndex(max(index, 0))
        self.specialty_filter.blockSignals(False)
        self._render_rows()

    def _render_rows(self, _index: int | None = None) -> None:
        specialty_id = self.specialty_filter.currentData()
        state = self.status_filter.currentData()
        names = {
            item.get("SpecialtyID"): str(item.get("SpecialtyName") or "Chưa đặt tên")
            for item in self._specialties
        }
        matching = [
            charge for charge in self._charges
            if (specialty_id is None or charge.get("specialty_id") == specialty_id)
            and (state == "all" or bool(charge.get("is_active")) == (state == "active"))
        ]
        matching.sort(
            key=lambda item: (names.get(item.get("specialty_id"), ""), str(item.get("effective_from", ""))),
            reverse=True,
        )
        self.table.set_rows([
            {
                "specialty": names.get(charge.get("specialty_id"), "Chuyên khoa không xác định"),
                "code": str(charge.get("code") or "—"),
                "name": str(charge.get("display_name") or "—"),
                "price": _price_text(charge.get("unit_price")),
                "effective_from": _date_text(charge.get("effective_from")),
                "status": "ACTIVE" if charge.get("is_active") else "INACTIVE",
            }
            for charge in matching
        ])
        self.row_count_label.setText(f"{len(matching)} phiên bản giá phù hợp")

    def _build_create_dialog(self) -> tuple[AdminFormDialog, ChevronComboBox, QLineEdit, QLineEdit, QLineEdit]:
        dialog = AdminFormDialog(
            "Thêm phiên bản phí khám",
            "Mã giá phải mới. Giá hiện hành của chuyên khoa sẽ tự ngừng hiệu lực khi lưu.",
            self,
            save_text="Lưu giá mới",
        )
        specialty = ChevronComboBox()
        specialty.setAccessibleName("Chuyên khoa áp dụng phí khám")
        specialty.addItem("Chọn chuyên khoa", None)
        for item in sorted(self._specialties, key=lambda entry: str(entry.get("SpecialtyName", ""))):
            if item.get("IsActive"):
                specialty.addItem(str(item.get("SpecialtyName") or "—"), item.get("SpecialtyID"))
        code = QLineEdit()
        code.setMaxLength(50)
        code.setPlaceholderText("Ví dụ: KHAM-NOI-2026-01")
        code.setAccessibleName("Mã phiên bản giá")
        name = QLineEdit()
        name.setMaxLength(200)
        name.setPlaceholderText("Ví dụ: Phí khám Nội tổng quát")
        name.setAccessibleName("Tên khoản thu")
        price = QLineEdit()
        price.setMaxLength(19)
        price.setPlaceholderText("Số VND, ví dụ: 150000")
        price.setAccessibleName("Đơn giá VND")
        dialog.add_field("Chuyên khoa", specialty, 0, 0, required=True)
        dialog.add_field("Mã phiên bản", code, 0, 1, required=True)
        dialog.add_field("Tên khoản thu", name, 1, 0, required=True, column_span=2)
        dialog.add_field("Đơn giá (VND)", price, 2, 0, required=True, column_span=2)
        return dialog, specialty, code, name, price

    def open_create_dialog(self) -> None:
        if not any(item.get("IsActive") for item in self._specialties):
            self.feedback.show_message(
                "Chưa có chuyên khoa",
                "Cần tạo một chuyên khoa đang hoạt động trước khi thêm phí khám.",
                severity="error",
            )
            return
        dialog, specialty, code, name, price = self._build_create_dialog()
        dialog.buttons.accepted.connect(
            lambda: self._submit_create(dialog, specialty, code, name, price)
        )
        dialog.exec()

    def _submit_create(
        self,
        dialog: AdminFormDialog,
        specialty: ChevronComboBox,
        code: QLineEdit,
        name: QLineEdit,
        price: QLineEdit,
    ) -> None:
        specialty_id = specialty.currentData()
        code_text = code.text().strip()
        name_text = name.text().strip()
        price_text = price.text().strip()
        if not isinstance(specialty_id, int):
            dialog.show_request_error("Thiếu thông tin", "Vui lòng chọn chuyên khoa.")
            return
        if not _CODE_PATTERN.fullmatch(code_text):
            dialog.show_request_error("Mã giá không hợp lệ", "Nhập mã mới gồm 2–50 chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.")
            return
        if not name_text:
            dialog.show_request_error("Thiếu thông tin", "Vui lòng nhập tên khoản thu.")
            return
        if not _PRICE_PATTERN.fullmatch(price_text) or Decimal(price_text) <= 0:
            dialog.show_request_error("Đơn giá không hợp lệ", "Nhập số VND dương, tối đa 16 chữ số và 2 chữ số thập phân; không dùng dấu phân cách hàng nghìn.")
            return

        payload = {
            "code": code_text,
            "display_name": name_text,
            "category": "CONSULTATION",
            "specialty_id": specialty_id,
            "unit_price": str(Decimal(price_text).quantize(Decimal("0.01"))),
        }
        dialog.set_busy(True)
        self.run_admin_task(
            "create-consultation-fee",
            lambda: require_success(
                api_client.post("/api/v1/catalog/charges", json=payload),
                "Không thể thêm phí khám.",
            ),
            lambda _response: self._saved(dialog),
            on_finished=lambda: dialog.set_busy(False),
            on_error=lambda error: dialog.show_request_error(
                "Không thể lưu phí khám", self.error_message(error)
            ),
            loading_text="Đang lưu phiên bản giá…",
        )

    def _saved(self, dialog: AdminFormDialog) -> None:
        dialog.accept()
        self.feedback.show_message(
            "Đã lưu giá mới",
            "Giá cũ vẫn còn trong lịch sử và hóa đơn đã lập không bị thay đổi.",
            severity="success",
        )
        self.load_data(clear_feedback=False)
