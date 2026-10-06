"""Central, non-blocking login window for ClinicManagement."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt, QThreadPool, QTimer, Slot
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.api.workers import ApiWorker
from frontend.api_client import api_client
from frontend.core.config import get_frontend_settings
from frontend.views.register_view import RegisterView
from frontend.widgets.feedback_banner import FeedbackBanner


class LoginWindow(QWidget):
    def __init__(self, on_success: Callable[[], None]):
        super().__init__()
        self.on_success = on_success
        self._login_worker: ApiWorker | None = None
        self._register_dialog: QDialog | None = None
        self._routing_pending = False
        self.setWindowTitle("Đăng nhập - Clinic Management")
        self.resize(440, 680)
        self.setMinimumSize(400, 640)

        # Center layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setAlignment(Qt.AlignCenter)

        # Card container
        card = QFrame()
        card.setObjectName("authCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(16)

        # Header branding
        tag_label = QLabel("HỆ THỐNG Y TẾ")
        tag_label.setObjectName("authTagLabel")
        tag_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(tag_label)

        title_label = QLabel("Clinic Management")
        title_label.setObjectName("authMainTitle")
        title_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(title_label)

        subtitle_label = QLabel("Đăng nhập để tiếp tục")
        subtitle_label.setObjectName("mutedLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setWordWrap(True)
        card_layout.addWidget(subtitle_label)

        card_layout.addSpacing(8)

        # Inline error banner
        self.error_label = QLabel()
        self.error_label.setObjectName("loginErrorBanner")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        card_layout.addWidget(self.error_label)
        self.feedback = FeedbackBanner(self)
        card_layout.addWidget(self.feedback)
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.timeout.connect(self.feedback.clear)

        # Username input
        user_box = QVBoxLayout()
        user_box.setSpacing(6)
        user_label = QLabel("Tên đăng nhập")
        user_label.setObjectName("fieldLabel")
        self.username_input = QLineEdit()
        self.username_input.setAccessibleName("Tên đăng nhập")
        self.username_input.setPlaceholderText("Nhập tên đăng nhập...")
        self.username_input.returnPressed.connect(self.handle_login)
        user_box.addWidget(user_label)
        user_box.addWidget(self.username_input)
        card_layout.addLayout(user_box)

        # Password input
        pwd_box = QVBoxLayout()
        pwd_box.setSpacing(6)
        pwd_label = QLabel("Mật khẩu")
        pwd_label.setObjectName("fieldLabel")
        self.password_input = QLineEdit()
        self.password_input.setAccessibleName("Mật khẩu")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Nhập mật khẩu...")
        self.password_input.returnPressed.connect(self.handle_login)
        pwd_box.addWidget(pwd_label)
        pwd_box.addWidget(self.password_input)
        card_layout.addLayout(pwd_box)

        card_layout.addSpacing(6)

        # Login button
        self.login_btn = QPushButton("Đăng nhập")
        self.login_btn.setObjectName("primaryButton")
        self.login_btn.setMinimumHeight(40)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setAccessibleName("Đăng nhập")
        card_layout.addWidget(self.login_btn)

        self.register_btn = QPushButton("Đăng ký tài khoản bệnh nhân")
        self.register_btn.setVisible(get_frontend_settings().app_mode != "production")
        self.register_btn.setObjectName("secondaryButton")
        self.register_btn.setMinimumHeight(40)
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setAccessibleName("Đăng ký tài khoản bệnh nhân")
        self.register_btn.clicked.connect(self.open_registration)
        card_layout.addWidget(self.register_btn)

        main_layout.addWidget(card)

    def handle_login(self) -> None:
        if self._login_worker is not None:
            return
        self.error_label.setVisible(False)
        username = self.username_input.text().strip()
        password = self.password_input.text()
        self._set_field_error(self.username_input, not username)
        self._set_field_error(self.password_input, not password)

        if not username or not password:
            self.error_label.setText("Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu.")
            self.error_label.setVisible(True)
            return

        worker = ApiWorker(lambda: api_client.login(username, password))
        self._login_worker = worker
        self._sync_busy_state()
        worker.signals.success.connect(self._login_finished)
        worker.signals.error.connect(self._login_failed)
        worker.signals.finished.connect(self._login_cleanup)
        QThreadPool.globalInstance().start(worker)

    @Slot(object)
    def _login_finished(self, result: Any) -> None:
        ok, error = result
        if ok:
            self.on_success()
            return
        self._show_error(error or "Sai tài khoản hoặc mật khẩu.")

    @Slot(object)
    def _login_failed(self, _error: Exception) -> None:
        self._show_error("Không thể xử lý đăng nhập. Vui lòng thử lại.")

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self._set_field_error(self.password_input, True)
        self.password_input.clear()
        self.password_input.setFocus()

    @staticmethod
    def _set_field_error(field: QLineEdit, active: bool) -> None:
        field.setProperty("hasError", active)
        field.style().unpolish(field)
        field.style().polish(field)

    @Slot()
    def _login_cleanup(self) -> None:
        self._login_worker = None
        self.password_input.clear()
        self._sync_busy_state()

    def set_routing_pending(self, pending: bool) -> None:
        """Keep credentials locked while an asynchronous role route is resolving."""

        self._routing_pending = pending
        self._sync_busy_state()

    def open_registration(self) -> None:
        """Open the existing patient-only registration form from central login."""

        if self._register_dialog is not None:
            self._register_dialog.raise_()
            self._register_dialog.activateWindow()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Đăng ký tài khoản bệnh nhân")
        dialog.setModal(True)
        dialog.resize(620, 760)
        layout = QVBoxLayout(dialog)
        registration = RegisterView(api_client, dialog)
        layout.addWidget(registration)
        self._register_dialog = dialog

        registration.back_requested.connect(dialog.reject)
        registration.registration_succeeded.connect(
            lambda username: self._registration_finished(dialog, username)
        )
        dialog.finished.connect(lambda _result: self._clear_registration_dialog(dialog))
        dialog.exec()

    def _registration_finished(self, dialog: QDialog, username: str) -> None:
        dialog.accept()
        self.username_input.setText(username)
        self.password_input.clear()
        self.feedback.show_message(
            "Tạo tài khoản thành công",
            "Tài khoản bệnh nhân đã sẵn sàng. Hãy nhập mật khẩu để đăng nhập.",
            severity="success",
        )
        self._feedback_timer.start(4000)
        self.username_input.setFocus()

    def _clear_registration_dialog(self, dialog: QDialog) -> None:
        if self._register_dialog is dialog:
            self._register_dialog = None

    def reset_for_login(self) -> None:
        """Remove sensitive state before presenting the central login again."""

        self._routing_pending = False
        self._feedback_timer.stop()
        self.password_input.clear()
        self.error_label.clear()
        self.error_label.setVisible(False)
        self.feedback.clear()
        self._set_field_error(self.username_input, False)
        self._set_field_error(self.password_input, False)
        self._sync_busy_state()

    def _sync_busy_state(self) -> None:
        login_pending = self._login_worker is not None
        busy = login_pending or self._routing_pending
        self.username_input.setEnabled(not busy)
        self.password_input.setEnabled(not busy)
        self.login_btn.setEnabled(not busy)
        self.register_btn.setEnabled(not busy)
        if login_pending:
            self.login_btn.setText("Đang đăng nhập...")
        elif self._routing_pending:
            self.login_btn.setText("Đang mở ứng dụng...")
        else:
            self.login_btn.setText("Đăng nhập")
