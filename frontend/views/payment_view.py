"""Payment Processing View for Clinic Cashier & Reception."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.config import get_frontend_settings
from frontend.views.common import BaseApiView, format_money
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadge


def demo_transfer_payload(invoice_id: int, amount: Decimal) -> str:
    """Local demonstration data: no payment URL or bank account is encoded."""
    return f"CLINIC-DEMO|{invoice_id}|{amount:.2f}"


def parse_tendered(text: str) -> Decimal:
    """Accept Vietnamese grouping and at most two decimal places."""
    value = text.strip().replace(" ", "")
    if not value:
        raise ValueError("Vui lòng nhập số tiền khách đưa.")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    elif value.count(".") > 1 or ("." in value and len(value.rsplit(".", 1)[1]) == 3):
        value = value.replace(".", "")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Số tiền khách đưa không hợp lệ.") from exc
    if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
        raise ValueError("Số tiền khách đưa không hợp lệ.")
    return amount


class PaymentView(BaseApiView):
    """Collect cash or record a manually verified bank transfer."""

    payment_completed = Signal(int)  # payment_id

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._production_mode = get_frontend_settings().app_mode == "production"
        self._current_invoice: dict[str, Any] | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.header = PageHeader(
            "Thu phí",
            "Tìm hóa đơn, ghi nhận thanh toán và xuất biên lai.",
            parent=self,
        )
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Invoice Search / Select Card
        lookup_card = QFrame()
        lookup_card.setObjectName("filterCard")
        lookup_layout = QHBoxLayout(lookup_card)
        lookup_layout.setContentsMargins(18, 14, 18, 14)
        lookup_layout.setSpacing(12)

        lookup_label = QLabel("Tìm hóa đơn")
        lookup_label.setObjectName("fieldLabel")
        lookup_layout.addWidget(lookup_label)

        self.inv_input = QLineEdit()
        self.inv_input.setPlaceholderText("Nhập mã hóa đơn hoặc số điện thoại")
        self.inv_input.setAccessibleName("Mã hóa đơn hoặc số điện thoại bệnh nhân")
        self.inv_input.returnPressed.connect(self._fetch_invoice)
        lookup_layout.addWidget(self.inv_input, 2)

        self.btn_find = QPushButton("Tìm hóa đơn")
        self.btn_find.setCursor(Qt.PointingHandCursor)
        self.btn_find.clicked.connect(self._fetch_invoice)
        lookup_layout.addWidget(self.btn_find)

        layout.addWidget(lookup_card)

        self.empty_prompt = EmptyState(
            "Chưa chọn hóa đơn",
            "Nhập mã hóa đơn hoặc số điện thoại bệnh nhân để bắt đầu thu phí.",
            icon="search",
        )
        layout.addWidget(self.empty_prompt)

        # Invoice Details & Settlement Panel
        self.settlement_card = QFrame()
        self.settlement_card.setObjectName("contentCard")
        settle_layout = QVBoxLayout(self.settlement_card)
        settle_layout.setContentsMargins(24, 20, 24, 20)
        settle_layout.setSpacing(16)

        # Bill details
        self.lbl_inv_title = QLabel("Thông tin hóa đơn")
        self.lbl_inv_title.setObjectName("sectionTitle")
        settle_layout.addWidget(self.lbl_inv_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Bệnh nhân:"), 0, 0)
        self.lbl_patient = QLabel("—")
        self.lbl_patient.setWordWrap(True)
        self.lbl_patient.setObjectName("fieldValueStrong")
        grid.addWidget(self.lbl_patient, 0, 1)

        grid.addWidget(QLabel("Bác sĩ:"), 0, 2)
        self.lbl_doctor = QLabel("—")
        self.lbl_doctor.setWordWrap(True)
        self.lbl_doctor.setObjectName("fieldValueStrong")
        grid.addWidget(self.lbl_doctor, 0, 3)

        grid.addWidget(QLabel("Trạng thái:"), 1, 0)
        self.badge_status = StatusBadge("UNPAID")
        grid.addWidget(self.badge_status, 1, 1)

        grid.addWidget(QLabel("Tổng cần thu:"), 1, 2)
        self.lbl_total = QLabel("0 ₫")
        self.lbl_total.setObjectName("amountDue")
        grid.addWidget(self.lbl_total, 1, 3)

        settle_layout.addLayout(grid)

        # Payment Method Selector
        settle_layout.addSpacing(8)
        method_label = QLabel("Hình thức thanh toán:")
        method_label.setObjectName("sectionTitle")
        settle_layout.addWidget(method_label)

        self.method_group = QButtonGroup(self)
        method_row = QHBoxLayout()
        method_row.setSpacing(24)

        self.rb_cash = QRadioButton("Tiền mặt")
        self.rb_cash.setChecked(True)
        self.rb_cash.toggled.connect(self._on_method_changed)
        self.method_group.addButton(self.rb_cash)
        method_row.addWidget(self.rb_cash)

        self.rb_transfer = QRadioButton("Chuyển khoản (DEMO)")
        self.rb_transfer.toggled.connect(self._on_method_changed)
        self.method_group.addButton(self.rb_transfer)
        method_row.addWidget(self.rb_transfer)

        method_row.addStretch(1)
        settle_layout.addLayout(method_row)

        # Cash Calculation Box
        self.cash_box = QFrame()
        self.cash_box.setObjectName("cashBox")
        cash_layout = QGridLayout(self.cash_box)
        cash_layout.setContentsMargins(16, 14, 16, 14)
        cash_layout.setSpacing(12)

        cash_layout.addWidget(QLabel("Tiền khách đưa:"), 0, 0)
        self.cash_input = QLineEdit()
        self.cash_input.textChanged.connect(self._calculate_change)
        cash_layout.addWidget(self.cash_input, 0, 1)

        cash_layout.addWidget(QLabel("Tiền thối lại:"), 1, 0)
        self.lbl_change = QLabel("0 ₫")
        self.lbl_change.setObjectName("changeAmount")
        cash_layout.addWidget(self.lbl_change, 1, 1)

        settle_layout.addWidget(self.cash_box)

        self.transfer_box = QFrame()
        self.transfer_box.setObjectName("filterCard")
        transfer_layout = QVBoxLayout(self.transfer_box)
        self.qr_title = QLabel("QR MÔ PHỎNG · KHÔNG THỂ THANH TOÁN")
        self.qr_title.setObjectName("sectionTitle")
        transfer_layout.addWidget(self.qr_title)
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setAccessibleName("Mã QR mô phỏng, không có tài khoản ngân hàng")
        transfer_layout.addWidget(self.qr_label)
        self.transfer_note = QLabel(
            "Mã QR chỉ chứa mã hóa đơn và số tiền DEMO; không có tài khoản ngân hàng. "
            "Việc mở QR không ghi nhận thanh toán. Nhân viên chỉ bấm xác nhận sau khi đối chiếu."
        )
        self.transfer_note.setWordWrap(True)
        transfer_layout.addWidget(self.transfer_note)
        self.transfer_reference_label = QLabel("Mã giao dịch trên sao kê ngân hàng:")
        transfer_layout.addWidget(self.transfer_reference_label)
        self.transfer_reference_input = QLineEdit()
        self.transfer_reference_input.setMaxLength(100)
        self.transfer_reference_input.setPlaceholderText("Nhập mã giao dịch đã đối chiếu")
        transfer_layout.addWidget(self.transfer_reference_input)
        self.transfer_verified_check = QCheckBox(
            "Tôi đã đối chiếu đúng mã giao dịch, số tiền và người nhận trên sao kê ngân hàng."
        )
        transfer_layout.addWidget(self.transfer_verified_check)
        self.rb_transfer.setText("Chuyển khoản xác nhận thủ công" if self._production_mode else "Chuyển khoản (DEMO)")
        self.qr_title.setVisible(not self._production_mode)
        self.qr_label.setVisible(not self._production_mode)
        self.transfer_note.setVisible(not self._production_mode)
        self.transfer_reference_label.setVisible(self._production_mode)
        self.transfer_reference_input.setVisible(self._production_mode)
        self.transfer_verified_check.setVisible(self._production_mode)
        self.transfer_box.hide()
        settle_layout.addWidget(self.transfer_box)

        # Confirm Button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_pay = QPushButton("Xác nhận thu")
        self.btn_pay.setObjectName("successButton")
        self.btn_pay.setCursor(Qt.PointingHandCursor)
        self.btn_pay.clicked.connect(self._process_payment)
        btn_row.addWidget(self.btn_pay)

        settle_layout.addLayout(btn_row)
        layout.addWidget(self.settlement_card)
        self.settlement_card.hide()

        # Receipt Container
        self.receipt_card = QFrame()
        self.receipt_card.setObjectName("receiptCard")
        receipt_layout = QVBoxLayout(self.receipt_card)
        receipt_layout.setContentsMargins(24, 20, 24, 20)

        self.receipt_text = QLabel("Biên lai thu tiền")
        self.receipt_text.setWordWrap(True)
        self.receipt_text.setObjectName("receiptText")
        receipt_layout.addWidget(self.receipt_text)

        layout.addWidget(self.receipt_card)
        self.receipt_card.hide()

        layout.addStretch(1)

        scroll.setWidget(container)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def set_invoice_id(self, invoice_id: int) -> None:
        self.inv_input.setText(str(invoice_id))
        self._fetch_invoice()

    def _fetch_invoice(self) -> None:
        inv_text = self.inv_input.text().strip()
        if not inv_text:
            self.feedback.show_message(
                "Thiếu thông tin",
                "Vui lòng nhập mã hóa đơn hoặc số điện thoại bệnh nhân.",
                severity="info",
            )
            return

        clean_id = inv_text.lstrip("#").upper().replace("INV-", "").replace("INV", "").strip()
        if clean_id.isdigit():
            inv_id = int(clean_id)
            self.run_api_task(
                f"get_inv_{inv_id}",
                lambda: self.api_client.get(f"/api/v1/reception/invoices/{inv_id}"),
                self._show_invoice_details,
                loading_text="Đang tải thông tin hóa đơn...",
            )
        else:
            self.run_api_task(
                f"search_inv_{inv_text}",
                lambda: self.api_client.get(
                    "/api/v1/reception/invoices", params={"keyword": inv_text}
                ),
                self._on_invoice_search_loaded,
                loading_text="Đang tìm kiếm hóa đơn...",
            )

    def _on_invoice_search_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        if not items:
            self.feedback.show_message(
                "Không tìm thấy", "Không tìm thấy hóa đơn phù hợp với từ khóa.", severity="error"
            )
            self._current_invoice = None
            self.settlement_card.hide()
            self.receipt_card.hide()
            self.empty_prompt.show()
            return
        self._show_invoice_details(items[0])

    def _show_invoice_details(self, matched: dict[str, Any]) -> None:
        self._current_invoice = matched
        self.empty_prompt.hide()
        self.settlement_card.show()
        self.receipt_card.hide()

        inv_id = matched.get("invoice_id", 0)
        self.lbl_inv_title.setText(f"Hóa đơn INV-{inv_id:04d}")
        self.lbl_patient.setText(
            f"{matched.get('patient_name')} ({matched.get('patient_phone') or 'Không có SĐT'})"
        )
        self.lbl_doctor.setText(matched.get("doctor_name", ""))
        self.badge_status.set_status(matched.get("status", "UNPAID"))

        amount = Decimal(str(matched.get("total_amount", 0)))
        self.lbl_total.setText(format_money(amount))
        self.cash_input.setText(f"{amount:.0f}" if amount == amount.to_integral() else f"{amount:.2f}")
        self.transfer_reference_input.clear()
        self.transfer_verified_check.setChecked(False)
        self._on_method_changed()
        self._calculate_change()

        if matched.get("status") == "PAID":
            self.btn_pay.setEnabled(False)
            self.feedback.show_message(
                "Đã thanh toán", "Hóa đơn này đã được thanh toán đầy đủ trước đó.", severity="info"
            )
        else:
            self.btn_pay.setEnabled(True)
            self.feedback.clear()

    def _on_method_changed(self) -> None:
        is_cash = self.rb_cash.isChecked()
        self.cash_box.setVisible(is_cash)
        self.transfer_box.setVisible(not is_cash)
        self.btn_pay.setText("Xác nhận thu tiền mặt" if is_cash else "Xác nhận đã nhận chuyển khoản")
        if not is_cash and self._current_invoice and not self._production_mode:
            self._show_demo_qr()

    def _show_demo_qr(self) -> None:
        if not self._current_invoice:
            return
        payload = demo_transfer_payload(
            int(self._current_invoice.get("invoice_id") or 0),
            Decimal(str(self._current_invoice.get("total_amount") or 0)),
        )
        try:
            import qrcode

            output = BytesIO()
            qrcode.make(payload, box_size=7, border=2).save(output, format="PNG")
            pixmap = QPixmap()
            if not pixmap.loadFromData(output.getvalue(), "PNG"):
                raise ValueError("Cannot decode demo QR image")
            self.qr_label.setPixmap(pixmap)
        except (ImportError, OSError, ValueError):
            self.qr_label.setText("Không thể tạo QR mô phỏng trên máy này.")
        self.qr_label.setToolTip(payload)

    def _calculate_change(self) -> None:
        if not self._current_invoice:
            return
        total = Decimal(str(self._current_invoice.get("total_amount", 0)))
        try:
            tendered = parse_tendered(self.cash_input.text())
        except ValueError:
            tendered = Decimal("0")
        change = max(Decimal("0"), tendered - total)
        self.lbl_change.setText(format_money(change))

    def _process_payment(self) -> None:
        if not self._current_invoice:
            return

        inv_id = self._current_invoice.get("invoice_id")
        method = "CASH" if self.rb_cash.isChecked() else "TRANSFER"
        total = Decimal(str(self._current_invoice.get("total_amount", 0)))
        amount = total

        if method == "CASH":
            try:
                amount = parse_tendered(self.cash_input.text())
            except ValueError as exc:
                self.feedback.show_message("Số tiền không hợp lệ", str(exc), severity="error")
                self.cash_input.setFocus()
                return
            if amount < total:
                self.feedback.show_message(
                    "Số tiền chưa đủ",
                    "Tiền khách đưa phải lớn hơn hoặc bằng tổng tiền cần thu.",
                    severity="error",
                )
                self.cash_input.setFocus()
                return

        if method == "TRANSFER" and self._production_mode:
            reference = self.transfer_reference_input.text().strip()
            if len(reference) < 3 or not self.transfer_verified_check.isChecked():
                self.feedback.show_message(
                    "Chưa đủ thông tin đối soát",
                    "Nhập mã giao dịch và xác nhận đã đối chiếu trên sao kê ngân hàng.",
                    severity="error",
                )
                self.transfer_reference_input.setFocus()
                return

        payload = {
            "payment_method": method,
            "amount": str(amount),
        }
        if method == "TRANSFER" and self._production_mode:
            payload["external_reference"] = reference
            payload["manual_verified"] = True

        self.run_api_task(
            f"pay_inv_{inv_id}",
            lambda: self.api_client.post(f"/api/v1/reception/invoices/{inv_id}/pay", json=payload),
            self._on_payment_success,
            loading_text="Đang xử lý thanh toán...",
            controls=(self.btn_pay,),
        )

    def _on_payment_success(self, res: dict[str, Any]) -> None:
        inv_id = res.get("invoice_id")
        total = Decimal(str(res.get("total_amount", 0)))
        method = res.get("payment_method", "CASH")
        patient_name = res.get("patient_name", "Bệnh nhân")
        method_str = "Tiền mặt" if method == "CASH" else (
            "Chuyển khoản đã đối soát" if self._production_mode else "Chuyển khoản (DEMO)"
        )
        tendered = Decimal(str(res.get("amount_received") or total))
        change = Decimal(str(res.get("change_due") or 0))

        self.feedback.show_message(
            "Thu tiền thành công",
            f"Hóa đơn INV-{inv_id:04d} đã được thanh toán thành công ({method_str})!",
            severity="success",
        )
        self._current_invoice = None
        self.settlement_card.hide()
        self.empty_prompt.hide()

        # Display Receipt
        receipt = f"""
==================================================
              PHÒNG KHÁM CLINICCARE
               BIÊN LAI THU VIỆN PHÍ
==================================================
Mã hóa đơn: INV-{inv_id:04d}
Bệnh nhân: {patient_name}
Bác sĩ khám: {res.get("doctor_name")}
Phương thức: {method_str}
--------------------------------------------------
TỔNG THANH TOÁN: {format_money(total)}
{f"TIỀN KHÁCH ĐƯA: {format_money(tendered)}" if method == "CASH" else ""}
{f"TIỀN THỪA: {format_money(change)}" if method == "CASH" else ""}
TRẠNG THÁI: ĐÃ THANH TOÁN
==================================================
           Cảm ơn Quý khách & Chúc mau khỏe!
"""
        self.receipt_text.setText(receipt)
        self.receipt_card.show()
        self.payment_completed.emit(inv_id)
