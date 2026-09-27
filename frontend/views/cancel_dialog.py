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
from frontend.views.common import format_date, format_time_range
from frontend.widgets.async_task_controller import AsyncTaskController


class CancelAppointmentDialog(QDialog):
    """Accessible cancellation dialog requiring explicit reason input."""

    appointment_canceled = Signal(dict)
    session_expired = Signal()

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
        self._tasks = AsyncTaskController(self)
        self.finished.connect(lambda _result: self._tasks.invalidate())

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
        summary_card.setObjectName("destructiveSummaryCard")
        card_layout = QVBoxLayout(summary_card)
        card_layout.setSpacing(6)

        doctor_info = appointment.get("doctor", {})
        doc_name = doctor_info.get("full_name", "Bác sĩ")
        spec_name = doctor_info.get("specialty", "")
        date_str = format_date(appointment.get("appointment_date"))
        time_str = format_time_range(
            appointment.get("start_time"),
            appointment.get("end_time"),
        )

        card_layout.addWidget(QLabel(f"<b>{t('field_doctor')}:</b> {doc_name} ({spec_name})"))
        card_layout.addWidget(QLabel(f"<b>{t('field_date')}:</b> {date_str}"))
        card_layout.addWidget(QLabel(f"<b>{t('field_time')}:</b> {time_str}"))
        layout.addWidget(summary_card)

        # Reason input
        lbl_reason = QLabel(t("cancel_reason_label"))
        lbl_reason.setObjectName("fieldLabel")
        layout.addWidget(lbl_reason)

        self.reason_edit = QTextEdit()
        self.reason_edit.setPlaceholderText(t("cancel_reason_placeholder"))
        self.reason_edit.setMaximumHeight(90)
        self.reason_edit.setTabChangesFocus(True)
        self.reason_edit.setAccessibleName(t("cancel_reason_label"))
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
        self.confirm_button.setDefault(True)
        self.confirm_button.clicked.connect(self._submit_cancel)
        btn_layout.addWidget(self.confirm_button)

        layout.addLayout(btn_layout)

    def _submit_cancel(self) -> None:
        if self._tasks.is_running("cancel"):
            return
        reason = self.reason_edit.toPlainText().strip()
        self.error_label.setVisible(False)
        self.confirm_button.setText(t("processing"))

        def operation() -> object:
            return self.api_client.post(
                f"/api/v1/appointments/{self.appointment_id}/cancel",
                json={"cancellation_reason": reason or None},
            )

        def succeeded(result: object) -> None:
            if isinstance(result, dict):
                self.appointment_canceled.emit(result)
            else:
                self.appointment_canceled.emit({})
            self.accept()

        def failed(error: Exception) -> None:
            if isinstance(error, ApiError) and error.status_code == 401:
                self.session_expired.emit()
                self.reject()
                return
            message = (
                error.message if isinstance(error, ApiError) else t("error_unexpected_message")
            )
            self.error_label.setText(message)
            self.error_label.setVisible(True)

        def finished() -> None:
            self.confirm_button.setText(t("confirm_cancel_btn"))

        self._tasks.run(
            "cancel",
            operation,
            succeeded,
            failed,
            controls=(self.reason_edit, self.back_button, self.confirm_button),
            on_finished=finished,
        )
