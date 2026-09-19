"""Patient login screen."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
        self.setObjectName("authPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.addStretch()

        shell = QWidget()
        shell.setMaximumWidth(990)
        shell_layout = QHBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(22)

        hero = QFrame()
        hero.setObjectName("authHero")
        hero.setMinimumWidth(350)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(34, 34, 34, 34)
        hero_layout.setSpacing(14)

        brand_row = QHBoxLayout()
        brand_mark = QLabel("+")
        brand_mark.setObjectName("authBrandMark")
        brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_mark.setFixedSize(42, 42)
        brand = QLabel("ClinicCare")
        brand.setObjectName("authBrand")
        brand_row.addWidget(brand_mark)
        brand_row.addWidget(brand)
        brand_row.addStretch()
        hero_layout.addLayout(brand_row)
        hero_layout.addStretch()

        hero_title = QLabel("Your health information,\nin one calm place.")
        hero_title.setObjectName("authHeroTitle")
        hero_title.setWordWrap(True)
        hero_layout.addWidget(hero_title)

        hero_text = QLabel(
            "Review appointments, medical records, prescriptions, and invoices "
            "through one secure patient portal."
        )
        hero_text.setObjectName("authHeroText")
        hero_text.setWordWrap(True)
        hero_layout.addWidget(hero_text)
        hero_layout.addSpacing(10)

        for feature in (
            "✓  Private access to your clinic records",
            "✓  Clear appointment and billing history",
            "✓  Designed for quick, simple follow-up",
        ):
            label = QLabel(feature)
            label.setObjectName("authHeroText")
            label.setWordWrap(True)
            hero_layout.addWidget(label)
        hero_layout.addStretch()

        secure = QLabel("SECURE PATIENT PORTAL")
        secure.setObjectName("sectionEyebrow")
        hero_layout.addWidget(secure)

        card = QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(390)
        card.setMaximumWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 36, 38, 36)
        card_layout.setSpacing(11)

        eyebrow = QLabel("WELCOME BACK")
        eyebrow.setObjectName("sectionEyebrow")
        title = QLabel("Sign in to ClinicCare")
        title.setObjectName("authTitle")
        subtitle = QLabel("Use your patient username to continue.")
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        card_layout.addWidget(eyebrow)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(12)

        username_label = QLabel("Username")
        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.username.setPlaceholderText("Enter your username")
        self.username.setClearButtonEnabled(True)
        self.username.setAccessibleName("Username")
        username_label.setBuddy(self.username)
        card_layout.addWidget(username_label)
        card_layout.addWidget(self.username)

        password_label = QLabel("Password")
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setPlaceholderText("Enter your password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setAccessibleName("Password")
        password_label.setBuddy(self.password)
        card_layout.addWidget(password_label)
        card_layout.addWidget(self.password)

        self.show_password = QCheckBox("Show password")
        self.show_password.setAccessibleName("Show password")
        self.show_password.toggled.connect(self._toggle_password)
        card_layout.addWidget(self.show_password)
        card_layout.addWidget(self.feedback)
        card_layout.addWidget(self.loading)

        self.login_button = QPushButton("Sign in")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setAccessibleName("Sign in")
        self.register_button = QPushButton("Create a patient account")
        self.register_button.setObjectName("secondaryButton")
        card_layout.addWidget(self.login_button)
        card_layout.addWidget(self.register_button)

        help_text = QLabel("Need help? Contact your clinic directly.")
        help_text.setObjectName("helperText")
        help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(help_text)

        shell_layout.addWidget(hero, 1)
        shell_layout.addWidget(card, 1)

        centered = QHBoxLayout()
        centered.addStretch()
        centered.addWidget(shell)
        centered.addStretch()
        root.addLayout(centered)
        root.addStretch()

        self.login_button.clicked.connect(self._login)
        self.register_button.clicked.connect(self.register_requested)
        self.username.returnPressed.connect(self._login)
        self.password.returnPressed.connect(self._login)
        self.username.setFocus()

    def set_username(self, username: str) -> None:
        self.username.setText(username)
        self.password.clear()
        self._clear_validation()
        self.password.setFocus()

    def reset(self) -> None:
        self.password.clear()
        self.show_password.setChecked(False)
        self._clear_validation()

    def _toggle_password(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)

    def _login(self) -> None:
        self._clear_validation()
        username = self.username.text().strip()
        password = self.password.text()
        if not username:
            self._show_validation(self.username, "Enter your username to continue.")
            return
        if not password:
            self._show_validation(self.password, "Enter your password to continue.")
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
            controls=(
                self.username,
                self.password,
                self.show_password,
                self.login_button,
                self.register_button,
            ),
            loading_text="Signing in…",
            expire_on_401=False,
        )

    def _show_validation(self, field: QLineEdit, message: str) -> None:
        field.setProperty("error", True)
        field.style().unpolish(field)
        field.style().polish(field)
        self.feedback.show_message("Check your details", message, severity="error")
        field.setFocus()
        field.selectAll()

    def _clear_validation(self) -> None:
        self.feedback.clear()
        for field in (self.username, self.password):
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)
