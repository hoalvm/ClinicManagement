"""Modal dialog for confirming and submitting appointment cancellations."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient, ApiError
from frontend.core.i18n import t


class CancelAppointmentDialog(QDialog):
    """Accessible cancellation dialog requiring explicit reason input."""

    appointment_canceled = Signal(dict)

    def __init__(
        self,
        api_client: ApiClient,
        appointment: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.appointment = appointment
        self.appointment_id = appointment.get("appointment_id", 0)

        self.setWindowTitle(t("cancel_dialog_title"))
        self.setModal(True)
        self.setMinimumWidth(440)
        self.resize(480, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel(t("cancel_dialog_title"))
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(t("cancel_dialog_desc"))
        subtitle.setObjectName("helperText")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Summary box
        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_card.setStyleSheet(
            "QFrame#card { background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 12px; }"
        )
        card_layout = QVBoxLayout(summary_card)
        card_layout.setSpacing(6)

        doctor_info = appointment.get("doctor", {})
        doc_name = doctor_info.get("full_name", "Bác sĩ")
        spec_name = doctor_info.get("specialty", "")
        date_str = appointment.get("appointment_date", "")
        time_str = f"{appointment.get('start_time', '')} - {appointment.get('end_time', '')}"

        card_layout.addWidget(QLabel(f"<b>Bác sĩ:</b> {doc_name} ({spec_name})"))
        card_layout.addWidget(QLabel(f"<b>Ngày khám:</b> {date_str}"))
        card_layout.addWidget(QLabel(f"<b>Khung giờ:</b> {time_str}"))
        layout.addWidget(summary_card)

        # Reason input
        lbl_reason = QLabel(t("cancel_reason_label"))
        lbl_reason.setObjectName("fieldLabel")
        layout.addWidget(lbl_reason)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(t("cancel_reason_placeholder"))
        self.reason_edit.setMaximumHeight(90)
        layout.addWidget(self.reason_edit)

        self.error_label = QLabel()
        self.error_label.setObjectName("errorText")
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        layout.addWidget(self.error_label)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch(1)

        self.back_button = QPushButton(t("close_btn"))
        self.back_button.setObjectName("secondaryButton")
        self.back_button.clicked.connect(self.reject)
        btn_layout.addWidget(self.back_button)

        self.confirm_button = QPushButton(t("confirm_cancel_btn"))
        self.confirm_button.setObjectName("dangerButton")
        self.confirm_button.setStyleSheet(
            "background: #dc2626; color: #ffffff; border: 1px solid #b91c1c; font-weight: 600; min-height: 38px; border-radius: 8px; padding: 0 16px;"
        )
        self.confirm_button.clicked.connect(self._submit_cancel)
        btn_layout.addWidget(self.confirm_button)

        layout.addLayout(btn_layout)

    def _submit_cancel(self) -> None:
        reason = self.reason_edit.toPlainText().strip()
        self.error_label.setVisible(False)
        self.confirm_button.setEnabled(False)
        self.confirm_button.setText("Đang xử lý…")

        try:
            result = self.api_client.post(
                f"/api/v1/appointments/{self.appointment_id}/cancel",
                json={"cancellation_reason": reason or None},
            )
            self.appointment_canceled.emit(result)
            self.accept()
        except ApiError as exc:
            self.error_label.setText(exc.message)
            self.error_label.setVisible(True)
            self.confirm_button.setEnabled(True)
            self.confirm_button.setText("Xác nhận hủy")
        except Exception as exc:
            self.error_label.setText(str(exc))
            self.error_label.setVisible(True)
            self.confirm_button.setEnabled(True)
            self.confirm_button.setText("Xác nhận hủy")
