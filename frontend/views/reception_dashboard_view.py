"""Reception Desk Dashboard for Clinic Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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
from frontend.widgets.stat_card import StatCard


class ReceptionDashboardView(BaseApiView):
    """Staff dashboard showing today's operational queue, status counts, and quick actions."""

    navigate_requested = Signal(str)
    check_in_requested = Signal(int)  # appointment_id
    create_invoice_requested = Signal(int)  # appointment_id

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)

        # Page Header
        self.header = PageHeader(
            "Tiếp đón",
            "Hàng đợi tiếp nhận và chỉ số hoạt động trong ngày",
            action_label="Làm mới",
            parent=self,
        )
        self.header.action_clicked.connect(self.refresh)
        content_layout.addWidget(self.header)
        content_layout.addWidget(self.feedback)
        content_layout.addWidget(self.loading)

        # Quick Actions Row
        quick_actions_box = QFrame()
        quick_actions_box.setObjectName("quickActionsBox")
        quick_actions_layout = QHBoxLayout(quick_actions_box)
        quick_actions_layout.setContentsMargins(16, 14, 16, 14)
        quick_actions_layout.setSpacing(12)

        quick_label = QLabel("Thao tác:")
        quick_label.setStyleSheet("font-weight: 700; color: #1e293b; font-size: 13px;")
        quick_actions_layout.addWidget(quick_label)

        self.btn_check_in = QPushButton("Tiếp nhận")
        self.btn_check_in.setStyleSheet("background-color: #0f766e; color: white; border-radius: 8px; padding: 8px 14px; font-weight: 600;")
        self.btn_check_in.clicked.connect(lambda: self.navigate_requested.emit("check_in"))
        quick_actions_layout.addWidget(self.btn_check_in)

        self.btn_book = QPushButton("Đặt lịch")
        self.btn_book.setStyleSheet("background-color: #0369a1; color: white; border-radius: 8px; padding: 8px 14px; font-weight: 600;")
        self.btn_book.clicked.connect(lambda: self.navigate_requested.emit("book_for_patient"))
        quick_actions_layout.addWidget(self.btn_book)

        self.btn_invoice = QPushButton("Lập hóa đơn")
        self.btn_invoice.setStyleSheet("background-color: #d97706; color: white; border-radius: 8px; padding: 8px 14px; font-weight: 600;")
        self.btn_invoice.clicked.connect(lambda: self.navigate_requested.emit("invoice_management"))
        quick_actions_layout.addWidget(self.btn_invoice)

        self.btn_payments = QPushButton("Thu phí")
        self.btn_payments.setStyleSheet("background-color: #15803d; color: white; border-radius: 8px; padding: 8px 14px; font-weight: 600;")
        self.btn_payments.clicked.connect(lambda: self.navigate_requested.emit("payment"))
        quick_actions_layout.addWidget(self.btn_payments)

        quick_actions_layout.addStretch(1)
        content_layout.addWidget(quick_actions_box)

        # Stat Cards Grid
        stats_row_1 = QHBoxLayout()
        stats_row_1.setSpacing(16)

        self.card_today = StatCard("Lịch hẹn hôm nay", "0", tone="brand", parent=self)
        self.card_pending = StatCard("Chờ xác nhận", "0", tone="warning", parent=self)
        self.card_checked_in = StatCard("Đang chờ khám", "0", tone="info", parent=self)
        self.card_unpaid = StatCard("Chưa thanh toán", "0", tone="danger", parent=self)

        stats_row_1.addWidget(self.card_today)
        stats_row_1.addWidget(self.card_pending)
        stats_row_1.addWidget(self.card_checked_in)
        stats_row_1.addWidget(self.card_unpaid)
        content_layout.addLayout(stats_row_1)

        # Waiting Room / Checked-In Queue Section
        section_label = QLabel("Bệnh nhân đang chờ khám")
        section_label.setStyleSheet("font-weight: 700; font-size: 15px; color: #0f172a; margin-top: 10px;")
        content_layout.addWidget(section_label)

        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(6)
        self.queue_table.setHorizontalHeaderLabels([
            "Mã hẹn", "Họ và tên", "Số điện thoại", "Bác sĩ", "Giờ khám", "Thao tác"
        ])
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.queue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.queue_table.setMinimumHeight(240)
        content_layout.addWidget(self.queue_table)

        self.empty_queue = EmptyState(
            "Hiện không có bệnh nhân chờ khám",
            "Bệnh nhân đã tiếp nhận sẽ hiển thị tại danh sách này.",
            parent=self,
        )
        content_layout.addWidget(self.empty_queue)
        self.empty_queue.hide()

        content_layout.addStretch(1)

        scroll.setWidget(container)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(scroll)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.run_api_task(
            "fetch_stats",
            lambda: self.api_client.get("/api/v1/reception/dashboard"),
            self._on_stats_loaded,
            loading_text="Đang cập nhật dữ liệu...",
        )

    def _on_stats_loaded(self, data: dict[str, Any]) -> None:
        self.card_today.set_value(str(data.get("today_total_appointments", 0)))
        self.card_pending.set_value(str(data.get("today_pending_confirm", 0)))
        self.card_checked_in.set_value(str(data.get("today_checked_in", 0)))
        self.card_unpaid.set_value(str(data.get("unpaid_invoices_count", 0)))

        recent = data.get("recent_checked_in", [])
        if not recent:
            self.queue_table.hide()
            self.empty_queue.show()
        else:
            self.empty_queue.hide()
            self.queue_table.show()
            self.queue_table.setRowCount(len(recent))

            for row, item in enumerate(recent):
                appt_id = item.get("appointment_id", 0)
                patient = item.get("patient", {})
                doctor = item.get("doctor", {})
                start_time = str(item.get("start_time", ""))[:5]

                self.queue_table.setItem(row, 0, QTableWidgetItem(f"#{appt_id}"))
                self.queue_table.setItem(row, 1, QTableWidgetItem(patient.get("full_name", "")))
                self.queue_table.setItem(row, 2, QTableWidgetItem(patient.get("phone", "") or "—"))
                self.queue_table.setItem(row, 3, QTableWidgetItem(doctor.get("full_name", "")))
                self.queue_table.setItem(row, 4, QTableWidgetItem(start_time))

                action_btn = QPushButton("Lập hóa đơn")
                action_btn.setStyleSheet("background-color: #0f766e; color: white; border-radius: 6px; padding: 4px 8px; font-weight: 600; font-size: 11px;")
                action_btn.clicked.connect(lambda _, a_id=appt_id: self.create_invoice_requested.emit(a_id))
                self.queue_table.setCellWidget(row, 5, action_btn)
