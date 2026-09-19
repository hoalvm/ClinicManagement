"""Patient login screen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient, ApiError
from frontend.views.common import BaseApiView, require_dict


class LoginView(BaseApiView):
    login_succeeded = Signal(str, object)
    register_requested = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.addStretch()

        card = QFrame()
        card.setObjectName("authCard")
        card.setMaximumWidth(440)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 34, 38, 34)
        card_layout.setSpacing(14)

        title = QLabel("Welcome back")
        title.setObjectName("authTitle")
        subtitle = QLabel("Sign in to view your clinic information")
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)

        card_layout.addWidget(QLabel("Username"))
        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.username.setPlaceholderText("Enter your username")
        self.username.setClearButtonEnabled(True)
        card_layout.addWidget(self.username)

        card_layout.addWidget(QLabel("Password"))
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        card_layout.addWidget(self.password)

        self.show_password = QCheckBox("Show password")
        self.show_password.toggled.connect(self._toggle_password)
        card_layout.addWidget(self.show_password)
        card_layout.addWidget(self.loading)

        self.login_button = QPushButton("Login")
        self.login_button.setObjectName("primaryButton")
        self.register_button = QPushButton("Create an account")
        self.register_button.setObjectName("secondaryButton")
        card_layout.addWidget(self.login_button)
        card_layout.addWidget(self.register_button)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()
        root.addLayout(row)
        root.addStretch()

        self.login_button.clicked.connect(self._login)
        self.register_button.clicked.connect(self.register_requested)
        self.username.returnPressed.connect(self._login)
        self.password.returnPressed.connect(self._login)

    def set_username(self, username: str) -> None:
        self.username.setText(username)
        self.password.clear()
        self.password.setFocus()

    def reset(self) -> None:
        self.password.clear()
        self.show_password.setChecked(False)

    def _toggle_password(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)

    def _login(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        if not username or not password:
            self._show_validation("Enter both your username and password.")
            return

        def authenticate() -> tuple[str, dict[str, Any]]:
            token_payload = require_dict(
                self.api_client.post(
                    "/api/v1/auth/login",
                    json={"username": username, "password": password},
                )
            )
            token = token_payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise ValueError("Missing access token")
            self.api_client.set_access_token(token)
            try:
                user = require_dict(self.api_client.get("/api/v1/auth/me"))
                if user.get("role") != "PATIENT" or user.get("patient_id") is None:
                    raise ApiError(
                        "This portal is available to patient accounts only.",
                        status_code=403,
                    )
            except Exception:
                self.api_client.clear_access_token()
                raise
            return token, user

        def authenticated(result: object) -> None:
            token, user = result  # type: ignore[misc]
            self.password.clear()
            self.login_succeeded.emit(token, user)

        self.run_api_task(
            "login",
            authenticate,
            authenticated,
            controls=(self.login_button, self.register_button),
            loading_text="Signing in…",
            expire_on_401=False,
        )

    def _show_validation(self, message: str) -> None:
        QMessageBox.warning(self, "Login", message)
