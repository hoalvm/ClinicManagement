"""Patient Fast Check-In View for Reception Staff."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
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


class CheckInView(BaseApiView):
    """Fast check-in desk for arriving patients with appointment search and arrival queue."""

    appointment_checked_in = Signal(int)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        self.header = PageHeader(
            "Tiếp nhận",
            "Xác nhận có mặt và cấp số khám",
            action_label="Làm mới",
            parent=self,
        )
        self.header.action_clicked.connect(self.refresh)
        layout.addWidget(self.header)
        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

        # Fast Intake Search Box
        intake_card = QFrame()
        intake_card.setObjectName("intakeCard")
        intake_card.setStyleSheet("background: white; border: 1px solid #cbd5e1; border-radius: 12px; padding: 16px;")
        intake_layout = QVBoxLayout(intake_card)

        card_title = QLabel("Tìm kiếm lịch hẹn")
        card_title.setStyleSheet("font-size: 14px; font-weight: 700; color: #0f172a;")
        intake_layout.addWidget(card_title)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("SĐT, họ tên hoặc mã hẹn...")
        self.search_input.returnPressed.connect(self.search_and_load)
        search_row.addWidget(self.search_input, 3)

        self.queue_num_input = QLineEdit()
        self.queue_num_input.setPlaceholderText("Số thứ tự")
        self.queue_num_input.setMaximumWidth(140)
        search_row.addWidget(self.queue_num_input, 1)

        self.btn_search = QPushButton("Tìm kiếm")
        self.btn_search.setStyleSheet("background-color: #0f766e; color: white; font-weight: 600; padding: 8px 16px; border-radius: 8px;")
        self.btn_search.clicked.connect(self.search_and_load)
        search_row.addWidget(self.btn_search)

        intake_layout.addLayout(search_row)
        layout.addWidget(intake_card)

        # Results table for check-in
        results_label = QLabel("Lịch hẹn chờ tiếp nhận")
        results_label.setStyleSheet("font-size: 13px; font-weight: 700; color: #334155; margin-top: 6px;")
        layout.addWidget(results_label)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Mã hẹn", "Ngày khám", "Giờ khám", "Bệnh nhân", "Số điện thoại", "Bác sĩ", "Thao tác"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setMinimumHeight(200)
        layout.addWidget(self.results_table)

        self.empty_results = EmptyState(
            "Không có lịch hẹn chờ tiếp nhận",
            "Tìm kiếm theo SĐT, họ tên hoặc mã hẹn.",
            parent=self,
        )
        layout.addWidget(self.empty_results)
        self.empty_results.hide()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        self.search_and_load()

    def search_and_load(self) -> None:
        keyword = self.search_input.text().strip() or None
        # We look for PENDING and CONFIRMED appointments
        params = {"page": 1, "page_size": 25}
        if keyword:
            params["keyword"] = keyword

        self.run_api_task(
            "load_checkin_candidates",
            lambda: self.api_client.get("/api/v1/reception/appointments", params=params),
            self._on_candidates_loaded,
            loading_text="Đang tìm lịch hẹn...",
        )

    def _on_candidates_loaded(self, data: dict[str, Any]) -> None:
        all_items = data.get("items", [])
        # Filter for check-in candidates (PENDING or CONFIRMED)
        items = [i for i in all_items if i.get("status") in ("CONFIRMED", "PENDING")]

        if not items:
            self.results_table.hide()
            self.empty_results.show()
            return

        self.empty_results.hide()
        self.results_table.show()
        self.results_table.setRowCount(len(items))

        for row, appt in enumerate(items):
            appt_id = appt.get("appointment_id", 0)
            appt_date = str(appt.get("appointment_date", ""))
            start_time = str(appt.get("start_time", ""))[:5]
            patient = appt.get("patient", {})
            doctor = appt.get("doctor", {})

            self.results_table.setItem(row, 0, QTableWidgetItem(f"#{appt_id}"))
            self.results_table.setItem(row, 1, QTableWidgetItem(appt_date))
            self.results_table.setItem(row, 2, QTableWidgetItem(start_time))
            self.results_table.setItem(row, 3, QTableWidgetItem(patient.get("full_name", "")))
            self.results_table.setItem(row, 4, QTableWidgetItem(patient.get("phone", "") or "—"))
            self.results_table.setItem(row, 5, QTableWidgetItem(doctor.get("full_name", "")))

            btn = QPushButton("Tiếp nhận")
            btn.setStyleSheet("background-color: #0f766e; color: white; border-radius: 6px; padding: 6px 12px; font-weight: 600;")
            btn.clicked.connect(lambda _, a_id=appt_id: self._execute_check_in(a_id))
            self.results_table.setCellWidget(row, 6, btn)

    def _execute_check_in(self, appt_id: int) -> None:
        queue_no = self.queue_num_input.text().strip() or None
        payload = {"queue_number": queue_no}

        self.run_api_task(
            f"do_checkin_{appt_id}",
            lambda: self.api_client.post(
                f"/api/v1/reception/appointments/{appt_id}/check-in",
                json=payload,
            ),
            lambda res: self._on_check_in_success(appt_id, queue_no),
            loading_text="Đang xác nhận tiếp nhận...",
        )

    def _on_check_in_success(self, appt_id: int, queue_no: str | None) -> None:
        msg = f"Tiếp nhận bệnh nhân cho lịch hẹn #{appt_id} thành công!"
        if queue_no:
            msg += f" (Số thứ tự: {queue_no})"
        self.feedback.show_message("Tiếp nhận thành công", msg, severity="success")
        self.queue_num_input.clear()
        self.appointment_checked_in.emit(appt_id)
        self.refresh()
