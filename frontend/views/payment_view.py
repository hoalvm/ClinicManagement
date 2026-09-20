"""Payment Processing View for Clinic Cashier & Reception."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
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
from frontend.views.common import BaseApiView
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadge


class PaymentView(BaseApiView):
    """View to collect and process patient payments via CASH or CARD."""

    payment_completed = Signal(int)  # payment_id

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._current_invoice: dict[str, Any] | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        self.header = PageHeader(
            "Payment Processing",
            "Collect clinic consultation fees, pharmacy charges, and issue receipts via Cash or Card.",
            parent=self,
        )
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Invoice Search / Select Card
        lookup_card = QFrame()
        lookup_card.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 18px;")
        lookup_layout = QHBoxLayout(lookup_card)

        lookup_label = QLabel("Invoice #:")
        lookup_label.setStyleSheet("font-weight: 700; color: #0f172a;")
        lookup_layout.addWidget(lookup_label)

        self.inv_input = QLineEdit()
        self.inv_input.setPlaceholderText("Enter Invoice ID (e.g. 1)")
        self.inv_input.returnPressed.connect(self._fetch_invoice)
        lookup_layout.addWidget(self.inv_input, 2)

        self.btn_find = QPushButton("Load Invoice")
        self.btn_find.setStyleSheet("background-color: #0f766e; color: white; font-weight: 600; padding: 6px 16px; border-radius: 6px;")
        self.btn_find.clicked.connect(self._fetch_invoice)
        lookup_layout.addWidget(self.btn_find)

        layout.addWidget(lookup_card)

        # Invoice Details & Settlement Panel
        self.settlement_card = QFrame()
        self.settlement_card.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 24px;")
        settle_layout = QVBoxLayout(self.settlement_card)
        settle_layout.setSpacing(16)

        # Bill details
        self.lbl_inv_title = QLabel("Invoice Details")
        self.lbl_inv_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #0f172a;")
        settle_layout.addWidget(self.lbl_inv_title)

        grid = QGridLayout()
        grid.setSpacing(10)

        grid.addWidget(QLabel("Patient:"), 0, 0)
        self.lbl_patient = QLabel("—")
        self.lbl_patient.setStyleSheet("font-weight: 600; color: #1e293b;")
        grid.addWidget(self.lbl_patient, 0, 1)

        grid.addWidget(QLabel("Doctor:"), 0, 2)
        self.lbl_doctor = QLabel("—")
        self.lbl_doctor.setStyleSheet("font-weight: 600; color: #1e293b;")
        grid.addWidget(self.lbl_doctor, 0, 3)

        grid.addWidget(QLabel("Status:"), 1, 0)
        self.badge_status = StatusBadge("UNPAID")
        grid.addWidget(self.badge_status, 1, 1)

        grid.addWidget(QLabel("Total Due:"), 1, 2)
        self.lbl_total = QLabel("0 ₫")
        self.lbl_total.setStyleSheet("font-size: 18px; font-weight: 800; color: #b91c1c;")
        grid.addWidget(self.lbl_total, 1, 3)

        settle_layout.addLayout(grid)

        # Payment Method Selector
        method_label = QLabel("Select Payment Method:")
        method_label.setStyleSheet("font-weight: 700; color: #0f172a; margin-top: 10px;")
        settle_layout.addWidget(method_label)

        self.method_group = QButtonGroup(self)
        method_row = QHBoxLayout()
        method_row.setSpacing(24)

        self.rb_cash = QRadioButton("Tiền mặt (CASH)")
        self.rb_cash.setChecked(True)
        self.rb_cash.toggled.connect(self._on_method_changed)
        self.method_group.addButton(self.rb_cash)
        method_row.addWidget(self.rb_cash)

        self.rb_card = QRadioButton("Thẻ ngân hàng (CARD / POS)")
        self.method_group.addButton(self.rb_card)
        method_row.addWidget(self.rb_card)

        method_row.addStretch(1)
        settle_layout.addLayout(method_row)

        # Cash Calculation Box
        self.cash_box = QFrame()
        self.cash_box.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;")
        cash_layout = QGridLayout(self.cash_box)

        cash_layout.addWidget(QLabel("Tiền khách đưa (Cash Tendered):"), 0, 0)
        self.cash_input = QLineEdit()
        self.cash_input.setPlaceholderText("Enter amount received in VND…")
        self.cash_input.textChanged.connect(self._calculate_change)
        cash_layout.addWidget(self.cash_input, 0, 1)

        cash_layout.addWidget(QLabel("Tiền thối lại (Change to return):"), 1, 0)
        self.lbl_change = QLabel("0 ₫")
        self.lbl_change.setStyleSheet("font-size: 16px; font-weight: 700; color: #15803d;")
        cash_layout.addWidget(self.lbl_change, 1, 1)

        settle_layout.addWidget(self.cash_box)

        # Confirm Button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_pay = QPushButton("Confirm Payment & Print Receipt")
        self.btn_pay.setStyleSheet("background-color: #15803d; color: white; font-weight: 700; font-size: 14px; padding: 12px 28px; border-radius: 8px;")
        self.btn_pay.clicked.connect(self._process_payment)
        btn_row.addWidget(self.btn_pay)

        settle_layout.addLayout(btn_row)
        layout.addWidget(self.settlement_card)
        self.settlement_card.hide()

        # Receipt Container
        self.receipt_card = QFrame()
        self.receipt_card.setStyleSheet("background: #f0fdf4; border: 2px dashed #16a34a; border-radius: 12px; padding: 24px;")
        receipt_layout = QVBoxLayout(self.receipt_card)

        self.receipt_text = QLabel("Receipt Preview")
        self.receipt_text.setStyleSheet("font-family: monospace; font-size: 13px; color: #14532d;")
        receipt_layout.addWidget(self.receipt_text)

        layout.addWidget(self.receipt_card)
        self.receipt_card.hide()

        layout.addStretch(1)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def set_invoice_id(self, invoice_id: int) -> None:
        self.inv_input.setText(str(invoice_id))
        self._fetch_invoice()

    def _fetch_invoice(self) -> None:
        inv_text = self.inv_input.text().strip()
        if not inv_text.isdigit():
            self.feedback.show_message("Invalid ID", "Please enter a valid numeric invoice ID.", severity="danger")
            return

        inv_id = int(inv_text)
        self.run_api_task(
            f"get_inv_{inv_id}",
            lambda: self.api_client.get("/api/v1/reception/invoices", params={"keyword": str(inv_id)}),
            self._on_invoice_loaded,
            loading_text="Fetching invoice details…",
        )

    def _on_invoice_loaded(self, data: dict[str, Any]) -> None:
        items = data.get("items", [])
        inv_id_target = int(self.inv_input.text().strip())
        matched = next((i for i in items if i.get("invoice_id") == inv_id_target), None)

        if not matched:
            self.feedback.show_message("Invoice Not Found", f"Could not find Invoice #{inv_id_target}.", severity="danger")
            self.settlement_card.hide()
            return

        self._current_invoice = matched
        self.settlement_card.show()
        self.receipt_card.hide()

        self.lbl_inv_title.setText(f"Invoice INV-{matched.get('invoice_id'):04d}")
        self.lbl_patient.setText(f"{matched.get('patient_name')} ({matched.get('patient_phone') or 'No phone'})")
        self.lbl_doctor.setText(matched.get("doctor_name", ""))
        self.badge_status.set_status(matched.get("status", "UNPAID"))

        amount = float(matched.get("total_amount", 0))
        self.lbl_total.setText(f"{amount:,.0f} ₫")
        self.cash_input.setText(f"{int(amount)}")
        self._calculate_change()

        if matched.get("status") == "PAID":
            self.btn_pay.setEnabled(False)
            self.feedback.show_message("Already Settled", "This invoice has already been fully paid.", severity="info")
        else:
            self.btn_pay.setEnabled(True)

    def _on_method_changed(self) -> None:
        is_cash = self.rb_cash.isChecked()
        self.cash_box.setVisible(is_cash)

    def _calculate_change(self) -> None:
        if not self._current_invoice:
            return
        total = float(self._current_invoice.get("total_amount", 0))
        text = self.cash_input.text().replace(",", "").replace(".", "").strip()
        tendered = float(text) if text.isdigit() else 0.0
        change = max(0.0, tendered - total)
        self.lbl_change.setText(f"{change:,.0f} ₫")

    def _process_payment(self) -> None:
        if not self._current_invoice:
            return

        inv_id = self._current_invoice.get("invoice_id")
        method = "CASH" if self.rb_cash.isChecked() else "CARD"
        amount = float(self._current_invoice.get("total_amount", 0))

        payload = {
            "payment_method": method,
            "amount": amount,
        }

        self.run_api_task(
            f"pay_inv_{inv_id}",
            lambda: self.api_client.post(f"/api/v1/reception/invoices/{inv_id}/pay", json=payload),
            self._on_payment_success,
            loading_text="Finalizing payment…",
        )

    def _on_payment_success(self, res: dict[str, Any]) -> None:
        inv_id = res.get("invoice_id")
        total = float(res.get("total_amount", 0))
        method = res.get("payment_method", "CASH")
        patient_name = res.get("patient_name", "Patient")

        self.feedback.show_message("Payment Successful", f"Payment for Invoice INV-{inv_id:04d} settled ({method})!", severity="success")
        self.settlement_card.hide()

        # Display Receipt
        receipt = f"""
==================================================
              PHÒNG KHÁM ĐA KHOA / CLINIC
            HÓA ĐƠN THANH TOÁN (PAYMENT RECEIPT)
==================================================
Hóa đơn / Invoice: INV-{inv_id:04d}
Bệnh nhân / Patient: {patient_name}
Bác sĩ khám / Doctor: {res.get('doctor_name')}
Phương thức / Method: {method}
--------------------------------------------------
TỔNG THANH TOÁN / TOTAL: {total:,.0f} ₫
TRẠNG THÁI / STATUS: ĐÃ THANH TOÁN (PAID)
==================================================
           Cảm ơn Quý khách & Chúc mau khỏe!
"""
        self.receipt_text.setText(receipt)
        self.receipt_card.show()
        self.payment_completed.emit(inv_id)
