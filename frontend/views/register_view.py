"""Patient registration screen, modern dual-panel UI synchronized with LoginView."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.i18n import get_i18n, t
from frontend.views.common import BaseApiView
from frontend.widgets.language_selector import LanguageSelector

NULL_DATE = QDate(1752, 9, 14)


class RegisterView(BaseApiView):
    back_requested = Signal()
    registration_succeeded = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self.setObjectName("authPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 8, 32, 10)

        # 1. Top bar with Language Selector
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.lang_selector = LanguageSelector(self, show_label=True)
        top_bar.addWidget(self.lang_selector)
        root.addLayout(top_bar)

        # 2. Scroll area containing the centered card
        scroll = QScrollArea()
        scroll.setObjectName("authScroll")
        scroll.setAccessibleName("Patient registration form")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        container.setObjectName("authContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        card = QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(560)
        card.setMaximumWidth(620)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 20, 36, 18)
        card_layout.setSpacing(5)

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

        # --- Section 1: Account Info ---
        self.account_section_label = QLabel()
        self.account_section_label.setObjectName("authSectionHeader")
        card_layout.addWidget(self.account_section_label)

        grid_acc = QGridLayout()
        grid_acc.setHorizontalSpacing(14)
        grid_acc.setVerticalSpacing(5)

        # Username
        self.username_label = QLabel()
        self.username_label.setObjectName("fieldLabel")
        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.username.setClearButtonEnabled(True)
        self.username.setAccessibleName("Username, required")
        self._add_grid_field(grid_acc, 0, 0, self.username_label, self.username, column_span=2)

        # Password & Confirm Password
        self.password_label = QLabel()
        self.password_label.setObjectName("fieldLabel")
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setAccessibleName("Password, required")
        self._add_grid_field(grid_acc, 1, 0, self.password_label, self.password)

        self.confirm_password_label = QLabel()
        self.confirm_password_label.setObjectName("fieldLabel")
        self.confirm_password = QLineEdit()
        self.confirm_password.setMaxLength(128)
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.setAccessibleName("Confirm password, required")
        self._add_grid_field(grid_acc, 1, 1, self.confirm_password_label, self.confirm_password)

        grid_acc.setColumnStretch(0, 1)
        grid_acc.setColumnStretch(1, 1)
        card_layout.addLayout(grid_acc)

        # --- Section 2: Personal Info ---
        self.personal_section_label = QLabel()
        self.personal_section_label.setObjectName("authSectionHeader")
        card_layout.addWidget(self.personal_section_label)

        grid_pers = QGridLayout()
        grid_pers.setHorizontalSpacing(14)
        grid_pers.setVerticalSpacing(5)

        # Full name
        self.full_name_label = QLabel()
        self.full_name_label.setObjectName("fieldLabel")
        self.full_name = QLineEdit()
        self.full_name.setMaxLength(100)
        self.full_name.setClearButtonEnabled(True)
        self.full_name.setAccessibleName("Full name, required")
        self._add_grid_field(grid_pers, 0, 0, self.full_name_label, self.full_name, column_span=2)

        # Phone & Email
        self.phone_label = QLabel()
        self.phone_label.setObjectName("fieldLabel")
        self.phone = QLineEdit()
        self.phone.setMaxLength(15)
        self.phone.setAccessibleName("Phone number")
        self._add_grid_field(grid_pers, 1, 0, self.phone_label, self.phone)

        self.email_label = QLabel()
        self.email_label.setObjectName("fieldLabel")
        self.email = QLineEdit()
        self.email.setMaxLength(100)
        self.email.setAccessibleName("Email address")
        self._add_grid_field(grid_pers, 1, 1, self.email_label, self.email)

        # Date of birth & Gender
        self.dob_label = QLabel()
        self.dob_label.setObjectName("fieldLabel")
        self.date_of_birth = QDateEdit()
        self.date_of_birth.setAccessibleName("Date of birth")
        self.date_of_birth.setCalendarPopup(True)
        self.date_of_birth.setDisplayFormat("dd/MM/yyyy")
        self.date_of_birth.setMinimumDate(NULL_DATE)
        self.date_of_birth.setMaximumDate(QDate.currentDate())
        self.date_of_birth.setDate(NULL_DATE)
        self._add_grid_field(grid_pers, 2, 0, self.dob_label, self.date_of_birth)

        self.gender_label = QLabel()
        self.gender_label.setObjectName("fieldLabel")
        self.gender = QComboBox()
        self.gender.setAccessibleName("Gender")
        self._add_grid_field(grid_pers, 2, 1, self.gender_label, self.gender)

        # Address
        self.address_label = QLabel()
        self.address_label.setObjectName("fieldLabel")
        self.address = QTextEdit()
        self.address.setTabChangesFocus(True)
        self.address.setAcceptRichText(False)
        self.address.setFixedHeight(48)
        self.address.setAccessibleName("Address")
        self._add_grid_field(grid_pers, 3, 0, self.address_label, self.address, column_span=2)

        grid_pers.setColumnStretch(0, 1)
        grid_pers.setColumnStretch(1, 1)
        card_layout.addLayout(grid_pers)
        card_layout.addSpacing(6)

        # Actions
        self.register_button = QPushButton()
        self.register_button.setObjectName("primaryButton")
        self.register_button.setCursor(Qt.PointingHandCursor)
        self.register_button.setMinimumHeight(40)
        self.register_button.setAccessibleName("Create patient account")

        self.back_button = QPushButton()
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setCursor(Qt.PointingHandCursor)
        self.back_button.setMinimumHeight(36)

        card_layout.addWidget(self.register_button)
        card_layout.addWidget(self.back_button)

        self.help_text = QLabel()
        self.help_text.setObjectName("helperText")
        self.help_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.help_text)

        container_layout.addWidget(card)
        scroll.setWidget(container)
        root.addWidget(scroll)

        self._form_controls = (
            self.username,
            self.password,
            self.confirm_password,
            self.full_name,
            self.phone,
            self.email,
            self.date_of_birth,
            self.gender,
            self.address,
            self.back_button,
            self.register_button,
        )
        self.back_button.clicked.connect(self.back_requested)
        self.register_button.clicked.connect(self._register)
        self.confirm_password.returnPressed.connect(self._register)

        QWidget.setTabOrder(self.username, self.password)
        QWidget.setTabOrder(self.password, self.confirm_password)
        QWidget.setTabOrder(self.confirm_password, self.full_name)
        QWidget.setTabOrder(self.full_name, self.phone)
        QWidget.setTabOrder(self.phone, self.email)
        QWidget.setTabOrder(self.email, self.date_of_birth)
        QWidget.setTabOrder(self.date_of_birth, self.gender)
        QWidget.setTabOrder(self.gender, self.address)
        QWidget.setTabOrder(self.address, self.register_button)
        QWidget.setTabOrder(self.register_button, self.back_button)

        get_i18n().language_changed.connect(self.retranslate_ui)
        self.retranslate_ui()

    @staticmethod
    def _add_grid_field(
        layout: QGridLayout,
        row: int,
        column: int,
        label: QLabel,
        field: QWidget,
        column_span: int = 1,
    ) -> None:
        wrapper = QWidget()
        wrapper.setObjectName("fieldWrapper")
        field_layout = QVBoxLayout(wrapper)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(3)
        label.setBuddy(field)
        field_layout.addWidget(label)
        field_layout.addWidget(field)
        layout.addWidget(wrapper, row, column, 1, column_span)

    def retranslate_ui(self) -> None:
        """Update all text in RegisterView according to current language."""
        self.tag_label.setText(t("register_eyebrow"))
        self.title_label.setText(t("register_title"))
        self.subtitle_label.setText(t("register_subtitle"))

        self.account_section_label.setText(t("account_info"))
        self.username_label.setText(f"{t('username')} *")
        self.username.setPlaceholderText(t("username_placeholder"))

        self.password_label.setText(f"{t('password')} *")
        self.password.setPlaceholderText(t("password_placeholder"))

        self.confirm_password_label.setText(f"{t('confirm_password')} *")
        self.confirm_password.setPlaceholderText(t("confirm_password_placeholder"))

        self.personal_section_label.setText(t("personal_info"))
        self.full_name_label.setText(f"{t('full_name')} *")
        self.full_name.setPlaceholderText(t("full_name_placeholder"))

        self.phone_label.setText(t("phone"))
        self.phone.setPlaceholderText(t("phone_placeholder"))

        self.email_label.setText(t("email"))
        self.email.setPlaceholderText(t("email_placeholder"))

        self.dob_label.setText(t("date_of_birth"))
        self.date_of_birth.setSpecialValueText(t("not_set"))

        self.gender_label.setText(t("gender"))
        curr_gender = self.gender.currentData()
        self.gender.clear()
        self.gender.addItem(t("not_set"), None)
        self.gender.addItem(t("gender_male"), "MALE")
        self.gender.addItem(t("gender_female"), "FEMALE")
        self.gender.addItem(t("gender_other"), "OTHER")
        idx = self.gender.findData(curr_gender)
        if idx >= 0:
            self.gender.setCurrentIndex(idx)

        self.address_label.setText(t("address"))
        self.address.setPlaceholderText(t("address_placeholder"))

        self.register_button.setText(t("submit_register"))
        self.back_button.setText(t("already_have_account"))
        self.help_text.setText(t("create_account_help"))

    def _register(self) -> None:
        self._clear_errors()
        selected_date = self.date_of_birth.date()
        payload = {
            "username": self.username.text().strip(),
            "password": self.password.text(),
            "confirm_password": self.confirm_password.text(),
            "full_name": self.full_name.text().strip(),
            "phone": self.phone.text().strip() or None,
            "email": self.email.text().strip() or None,
            "date_of_birth": (
                None if selected_date == NULL_DATE else selected_date.toString("yyyy-MM-dd")
            ),
            "gender": self.gender.currentData(),
            "address": self.address.toPlainText().strip() or None,
        }
        validation = self._validate(payload)
        if validation:
            self._show_validation(validation)
            return

        username = str(payload["username"])

        def registered(_result: object) -> None:
            self._clear_form()
            self.registration_succeeded.emit(username)

        loading_text = "Đang tạo tài khoản…" if get_i18n().current_language == "vi" else "Creating account…"
        self.run_api_task(
            "register",
            lambda: self.api_client.post("/api/v1/auth/register", json=payload),
            registered,
            controls=self._form_controls,
            loading_text=loading_text,
            expire_on_401=False,
        )

    def _show_validation(self, message: str) -> None:
        field: QWidget
        if message == t("err_username_required"):
            field = self.username
        elif message == t("err_password_len"):
            field = self.password
        elif message == t("err_password_match"):
            field = self.confirm_password
        elif message == t("err_fullname_required"):
            field = self.full_name
        elif message == t("err_email_invalid"):
            field = self.email
        elif message == t("err_phone_invalid"):
            field = self.phone
        else:
            field = self.address
        field.setProperty("error", True)
        field.style().unpolish(field)
        field.style().polish(field)
        field.setFocus()
        title = "Vui lòng kiểm tra lại" if get_i18n().current_language == "vi" else "Check your details"
        self.feedback.show_message(title, message, severity="error")

    def _clear_errors(self) -> None:
        self.feedback.clear()
        for field in (
            self.username,
            self.password,
            self.confirm_password,
            self.full_name,
            self.phone,
            self.email,
            self.address,
        ):
            field.setProperty("error", False)
            field.style().unpolish(field)
            field.style().polish(field)

    @staticmethod
    def _validate(payload: dict[str, object]) -> str | None:
        if not payload["username"]:
            return t("err_username_required")
        if len(str(payload["password"])) < 8:
            return t("err_password_len")
        if payload["password"] != payload["confirm_password"]:
            return t("err_password_match")
        if not payload["full_name"]:
            return t("err_fullname_required")
        email = payload["email"]
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(email)):
            return t("err_email_invalid")
        phone = payload["phone"]
        if phone and not re.fullmatch(r"\+?\d{7,14}", str(phone)):
            return t("err_phone_invalid")
        if len(str(payload["address"] or "")) > 255:
            return t("err_address_len")
        return None

    def _clear_form(self) -> None:
        for field in (
            self.username,
            self.password,
            self.confirm_password,
            self.full_name,
            self.phone,
            self.email,
            self.address,
        ):
            field.clear()
        self.date_of_birth.setDate(NULL_DATE)
        self.gender.setCurrentIndex(0)
        self._clear_errors()

    def clear_data(self) -> None:
        """Remove credentials and personal data when leaving registration."""
        self._clear_form()
