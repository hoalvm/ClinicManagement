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
from frontend.core.i18n import get_i18n, t
from frontend.views.common import BaseApiView, require_dict
from frontend.widgets.language_selector import LanguageSelector


class LoginView(BaseApiView):
    login_succeeded = Signal(str, object)
    register_requested = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self.setObjectName("authPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 16, 32, 24)

        # Top bar with Language Selector
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.lang_selector = LanguageSelector(self, show_label=True)
        top_bar.addWidget(self.lang_selector)
        root.addLayout(top_bar)
        root.addStretch()

        # Centered auth card
        card = QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(400)
        card.setMaximumWidth(450)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setSpacing(14)

        # Header branding - clean typography, NO ICONS
        self.tag_label = QLabel()
        self.tag_label.setObjectName("authTagLabel")
        self.tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.tag_label)

        self.title_label = QLabel("ClinicCare")
        self.title_label.setObjectName("authMainTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("mutedLabel")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        card_layout.addWidget(self.subtitle_label)

        card_layout.addSpacing(4)
        card_layout.addWidget(self.feedback)
        card_layout.addWidget(self.loading)

        # Username input
        user_box = QVBoxLayout()
        user_box.setSpacing(5)
        self.username_label = QLabel("Username")
        self.username_label.setObjectName("fieldLabel")
        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.username.setClearButtonEnabled(True)
        self.username.setAccessibleName("Username")
        self.username_label.setBuddy(self.username)
        user_box.addWidget(self.username_label)
        user_box.addWidget(self.username)
        card_layout.addLayout(user_box)

        # Password input
        pwd_box = QVBoxLayout()
        pwd_box.setSpacing(5)
        self.password_label = QLabel("Password")
        self.password_label.setObjectName("fieldLabel")
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setAccessibleName("Password")
        self.password_label.setBuddy(self.password)
        pwd_box.addWidget(self.password_label)
        pwd_box.addWidget(self.password)
        card_layout.addLayout(pwd_box)

        self.show_password = QCheckBox("Show password")
        self.show_password.setCursor(Qt.PointingHandCursor)
        self.show_password.setAccessibleName("Show password")
        self.show_password.toggled.connect(self._toggle_password)
        card_layout.addWidget(self.show_password)

        card_layout.addSpacing(4)

        self.login_button = QPushButton("Sign in")
        self.login_button.setObjectName("primaryButton")
        self.login_button.setCursor(Qt.PointingHandCursor)
        self.login_button.setMinimumHeight(42)
        self.login_button.setAccessibleName("Sign in")
        self.register_button = QPushButton("Create a patient account")
        self.register_button.setObjectName("secondaryButton")
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setMinimumHeight(40)
        card_layout.addWidget(self.login_button)
        card_layout.addWidget(self.register_button)

        self.help_text = QLabel("Need help? Contact your clinic directly.")
        self.help_text.setObjectName("helperText")
        self.help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.help_text)

        centered = QHBoxLayout()
        centered.addStretch()
        centered.addWidget(card)
        centered.addStretch()
        root.addLayout(centered)
        root.addStretch()

        self.login_button.clicked.connect(self._login)
        self.register_button.clicked.connect(self.register_requested)
        self.username.returnPressed.connect(self._login)
        self.password.returnPressed.connect(self._login)
        self.username.setFocus()

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        """Update all text in LoginView according to current language."""
        self.tag_label.setText(t("portal_tag"))
        self.title_label.setText(t("sign_in_title"))
        self.subtitle_label.setText(t("sign_in_subtitle"))
        self.username_label.setText(t("username"))
        self.username.setPlaceholderText(t("username_placeholder", default="Nhập tên đăng nhập..."))
        self.password_label.setText(t("password"))
        self.password.setPlaceholderText(t("password_placeholder", default="Nhập mật khẩu..."))
        self.show_password.setText(t("show_password"))
        self.login_button.setText(t("sign_in_button"))
        self.register_button.setText(t("create_account_button"))
        self.help_text.setText(t("need_help"))
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
            self._show_validation(self.username, t("err_username_required"))
            return
        if not password:
            self._show_validation(self.password, t("err_password_required"))
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
            loading_text=t("signing_in"),
            expire_on_401=False,
        )

    def _show_validation(self, field: QLineEdit, message: str) -> None:
        field.setProperty("error", True)
        field.style().unpolish(field)
        field.style().polish(field)
        self.feedback.show_message(t("check_details"), message, severity="error")
        field.setFocus()
        field.selectAll()

    def _clear_validation(self) -> None:
        self.feedback.clear()
        for field in (self.username, self.password):
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)
