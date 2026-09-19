"""Read-only invoice, line item, and payment details."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.ui.icons import apply_line_icon
from frontend.views.common import (
    BaseApiView,
    configure_table,
    display_text,
    format_date,
    format_datetime,
    format_money,
    require_dict,
    table_item,
)
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.page_header import PageHeader
from frontend.widgets.status_badge import StatusBadge


class InvoiceDetailView(BaseApiView):
    back_requested = Signal()
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._invoice_id: int | None = None
        self._appointment_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        self.header = PageHeader(
            "Invoice",
            "Review billed services, totals, and payment information.",
            show_back=True,
        )
        self.back_button = self.header.back_button
        # ``title`` is retained for existing callers that update the invoice ID.
        self.title = self.header.title_label
        self.appointment_button = QPushButton("View appointment")
        self.appointment_button.setObjectName("primaryButton")
        apply_line_icon(
            self.appointment_button,
            "calendar",
            "#FFFFFF",
            active_color="#FFFFFF",
            accessible_name="View related appointment",
        )
        self.header.add_action(self.appointment_button)
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAccessibleName("Invoice information")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 8, 4)
        content_layout.setSpacing(16)

        info = QFrame()
        info.setObjectName("infoCard")
        info_grid = QGridLayout(info)
        info_grid.setContentsMargins(24, 20, 24, 20)
        info_grid.setHorizontalSpacing(28)
        info_grid.setVerticalSpacing(12)
        overview_title = QLabel("Invoice overview")
        overview_title.setObjectName("sectionTitle")
        info_grid.addWidget(overview_title, 0, 0, 1, 2)
        self.values: dict[str, QLabel] = {}
        fields = [
            ("Appointment ID", "appointment_id"),
            ("Appointment date", "appointment_date"),
            ("Doctor", "doctor"),
            ("Total amount", "total"),
            ("Status", "status"),
        ]
        for row, (label, key) in enumerate(fields, start=1):
            field_label = QLabel(label)
            field_label.setObjectName("fieldLabel")
            field_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
            value: QLabel
            if key == "status":
                value = StatusBadge()
                value.setMaximumWidth(180)
            else:
                value = QLabel("—")
                value.setObjectName("fieldValue")
                value.setWordWrap(True)
                value.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                    | Qt.TextInteractionFlag.TextSelectableByKeyboard
                )
                value.setAccessibleName(label)
            info_grid.addWidget(field_label, row, 0, Qt.AlignmentFlag.AlignTop)
            info_grid.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.values[key] = value
        info_grid.setColumnMinimumWidth(0, 142)
        info_grid.setColumnStretch(1, 1)
        content_layout.addWidget(info)

        items_card = QFrame()
        items_card.setObjectName("tableCard")
        items_layout = QVBoxLayout(items_card)
        items_layout.setContentsMargins(20, 18, 20, 20)
        items_layout.setSpacing(12)
        item_title = QLabel("Invoice items")
        item_title.setObjectName("sectionTitle")
        items_layout.addWidget(item_title)
        self.items_table = QTableView()
        self.items_table.setAccessibleName("Invoice line items")
        self.items_model: QStandardItemModel = configure_table(
            self.items_table,
            ["Item", "Quantity", "Unit price", "Line total"],
            stretch_column=0,
            column_widths={0: 300, 1: 90, 2: 160, 3: 170},
        )
        self.items_table.setMinimumHeight(190)
        items_layout.addWidget(self.items_table)
        content_layout.addWidget(items_card)

        payment_title = QLabel("Payment")
        payment_title.setObjectName("sectionTitle")
        content_layout.addWidget(payment_title)
        self.payment_card = QFrame()
        self.payment_card.setObjectName("infoCard")
        payment_grid = QGridLayout(self.payment_card)
        payment_grid.setContentsMargins(24, 20, 24, 20)
        payment_grid.setHorizontalSpacing(28)
        payment_grid.setVerticalSpacing(12)
        self.payment_values: dict[str, QLabel] = {}
        for row, (label, key) in enumerate(
            [
                ("Payment method", "method"),
                ("Amount paid", "amount"),
                ("Payment date", "date"),
            ]
        ):
            field_label = QLabel(label)
            field_label.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setObjectName("fieldValue")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
                | Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            value.setAccessibleName(label)
            payment_grid.addWidget(field_label, row, 0, Qt.AlignmentFlag.AlignTop)
            payment_grid.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
            self.payment_values[key] = value
        payment_grid.setColumnMinimumWidth(0, 142)
        payment_grid.setColumnStretch(1, 1)
        self.not_paid = EmptyState(
            "Payment pending",
            "No payment has been recorded for this invoice yet.",
            icon="invoice",
        )
        content_layout.addWidget(self.payment_card)
        content_layout.addWidget(self.not_paid)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.header.back_requested.connect(self.back_requested.emit)
        self.appointment_button.clicked.connect(self._open_appointment)
        self.clear_data()

    def activate(self, invoice_id: int) -> None:
        self.invalidate_pending()
        self.clear_data()
        self._invoice_id = invoice_id
        self.title.setText(f"Invoice #{invoice_id:06d}")
        self.header.set_subtitle("Review billed services, totals, and payment information.")
        self.load()

    def load(self) -> None:
        if self._invoice_id is None:
            return
        invoice_id = self._invoice_id
        self.run_api_task(
            "invoice-detail",
            lambda: self.api_client.get(f"/api/v1/invoices/me/{invoice_id}"),
            self._render,
            controls=(self.appointment_button,),
            loading_text="Loading invoice…",
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        appointment = data.get("appointment") or {}
        doctor = appointment.get("doctor") or {}
        self._appointment_id = int(data["appointment_id"])
        self.appointment_button.show()
        values: dict[str, Any] = {
            "appointment_id": self._appointment_id,
            "appointment_date": format_date(appointment.get("appointment_date")),
            "doctor": doctor.get("full_name"),
            "total": format_money(data.get("total_amount")),
            "status": data.get("status"),
        }
        for key, value in values.items():
            label = self.values[key]
            if isinstance(label, StatusBadge):
                label.set_status(value)
            else:
                label.setText(display_text(value))

        self.items_model.removeRows(0, self.items_model.rowCount())
        for item in data.get("items", []):
            row = [
                table_item(item.get("item_name")),
                table_item(item.get("quantity")),
                table_item(format_money(item.get("unit_price"))),
                table_item(format_money(item.get("line_total"))),
            ]
            for numeric_item in row[1:]:
                numeric_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
            self.items_model.appendRow(row)

        payment = data.get("payment")
        if isinstance(payment, dict):
            self.payment_values["method"].setText(display_text(payment.get("payment_method")))
            self.payment_values["amount"].setText(format_money(payment.get("amount")))
            self.payment_values["date"].setText(format_datetime(payment.get("payment_date")))
            self.payment_card.show()
            self.not_paid.hide()
        else:
            self.payment_card.hide()
            self.not_paid.show()

    def _open_appointment(self) -> None:
        if self._appointment_id is not None:
            self.appointment_requested.emit(self._appointment_id)

    def clear_data(self) -> None:
        self._invoice_id = None
        self._appointment_id = None
        self.title.setText("Invoice")
        self.header.set_subtitle("Review billed services, totals, and payment information.")
        for value in self.values.values():
            if isinstance(value, StatusBadge):
                value.set_status(None)
            else:
                value.setText("—")
        for value in self.payment_values.values():
            value.setText("—")
        self.items_model.removeRows(0, self.items_model.rowCount())
        self.payment_card.hide()
        self.not_paid.hide()
        self.appointment_button.hide()
