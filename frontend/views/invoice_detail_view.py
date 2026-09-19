"""Read-only invoice, line item, and payment details."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtGui import QStandardItemModel
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
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


class InvoiceDetailView(BaseApiView):
    back_requested = Signal()
    appointment_requested = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self._invoice_id: int | None = None
        self._appointment_id: int | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.setObjectName("secondaryButton")
        self.title = QLabel("Invoice")
        self.title.setObjectName("pageTitle")
        header.addWidget(self.back_button)
        header.addWidget(self.title)
        header.addStretch()
        root.addLayout(header)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(16)

        info = QFrame()
        info.setObjectName("contentCard")
        info_grid = QGridLayout(info)
        info_grid.setContentsMargins(22, 18, 22, 18)
        self.values: dict[str, QLabel] = {}
        fields = [
            ("Appointment ID", "appointment_id"),
            ("Appointment Date", "appointment_date"),
            ("Doctor", "doctor"),
            ("Total Amount", "total"),
            ("Status", "status"),
        ]
        for index, (label, key) in enumerate(fields):
            row, pair = divmod(index, 2)
            field_label = QLabel(label)
            field_label.setObjectName("fieldLabel")
            value = QLabel("—")
            value.setWordWrap(True)
            info_grid.addWidget(field_label, row, pair * 2)
            info_grid.addWidget(value, row, pair * 2 + 1)
            self.values[key] = value
        content_layout.addWidget(info)

        item_title = QLabel("Invoice Items")
        item_title.setObjectName("sectionTitle")
        content_layout.addWidget(item_title)
        self.items_table = QTableView()
        self.items_model: QStandardItemModel = configure_table(
            self.items_table, ["Item", "Quantity", "Unit Price", "Line Total"]
        )
        self.items_table.setMinimumHeight(190)
        content_layout.addWidget(self.items_table)

        payment_title = QLabel("Payment")
        payment_title.setObjectName("sectionTitle")
        content_layout.addWidget(payment_title)
        self.payment_card = QFrame()
        self.payment_card.setObjectName("contentCard")
        payment_grid = QGridLayout(self.payment_card)
        payment_grid.setContentsMargins(22, 18, 22, 18)
        self.payment_values: dict[str, QLabel] = {}
        for index, (label, key) in enumerate(
            [
                ("Payment Method", "method"),
                ("Amount", "amount"),
                ("Payment Date", "date"),
            ]
        ):
            field_label = QLabel(label)
            field_label.setObjectName("fieldLabel")
            value = QLabel("—")
            payment_grid.addWidget(field_label, index, 0)
            payment_grid.addWidget(value, index, 1)
            self.payment_values[key] = value
        self.not_paid = QLabel("Not paid")
        self.not_paid.setObjectName("emptyState")
        content_layout.addWidget(self.payment_card)
        content_layout.addWidget(self.not_paid)

        actions = QHBoxLayout()
        actions.addStretch()
        self.appointment_button = QPushButton("View Appointment")
        self.appointment_button.setObjectName("primaryButton")
        actions.addWidget(self.appointment_button)
        content_layout.addLayout(actions)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self.back_button.clicked.connect(self.back_requested)
        self.appointment_button.clicked.connect(self._open_appointment)
        self.clear_data()

    def activate(self, invoice_id: int) -> None:
        self.invalidate_pending()
        self.clear_data()
        self._invoice_id = invoice_id
        self.title.setText(f"Invoice #{invoice_id:06d}")
        self.load()

    def load(self) -> None:
        if self._invoice_id is None:
            return
        invoice_id = self._invoice_id
        self.run_api_task(
            "invoice-detail",
            lambda: self.api_client.get(f"/api/v1/invoices/me/{invoice_id}"),
            self._render,
            controls=(self.back_button, self.appointment_button),
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
            self.values[key].setText(display_text(value))

        self.items_model.removeRows(0, self.items_model.rowCount())
        for item in data.get("items", []):
            self.items_model.appendRow(
                [
                    table_item(item.get("item_name")),
                    table_item(item.get("quantity")),
                    table_item(format_money(item.get("unit_price"))),
                    table_item(format_money(item.get("line_total"))),
                ]
            )

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
        for value in self.values.values():
            value.setText("—")
        for value in self.payment_values.values():
            value.setText("—")
        self.items_model.removeRows(0, self.items_model.rowCount())
        self.payment_card.hide()
        self.not_paid.show()
        self.appointment_button.hide()
