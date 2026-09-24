"""Patient registration screen."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, Signal
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
from frontend.views.common import BaseApiView

NULL_DATE = QDate(1752, 9, 14)


class RegisterView(BaseApiView):
    back_requested = Signal()
    registration_succeeded = Signal(str)

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(api_client, parent)
        self.setObjectName("authPage")

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        scroll = QScrollArea()
        scroll.setAccessibleName("Patient registration form")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        outer = QHBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch()

        card = QFrame()
        card.setObjectName("authCard")
        card.setMinimumWidth(720)
        card.setMaximumWidth(780)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(38, 32, 38, 32)
        card_layout.setSpacing(16)

        eyebrow = QLabel("CLINICCARE PATIENT PORTAL")
        eyebrow.setObjectName("sectionEyebrow")
        title = QLabel("Create your account")
        title.setObjectName("authTitle")
        subtitle = QLabel(
            "Set up secure access to your appointments, medical records, and invoices."
        )
        subtitle.setObjectName("mutedLabel")
        subtitle.setWordWrap(True)
        card_layout.addWidget(eyebrow)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addWidget(self.feedback)

        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.username.setPlaceholderText("Choose a username")
        self.username.setAccessibleName("Username, required")
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("At least 8 characters")
        self.password.setAccessibleName("Password, required")
        self.confirm_password = QLineEdit()
        self.confirm_password.setMaxLength(128)
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password.setPlaceholderText("Enter your password again")
        self.confirm_password.setAccessibleName("Confirm password, required")
        self.full_name = QLineEdit()
        self.full_name.setMaxLength(100)
        self.full_name.setPlaceholderText("Your full name")
        self.full_name.setAccessibleName("Full name, required")
        self.phone = QLineEdit()
        self.phone.setMaxLength(15)
        self.phone.setPlaceholderText("e.g. 0900000000")
        self.phone.setAccessibleName("Phone number")
        self.email = QLineEdit()
        self.email.setMaxLength(100)
        self.email.setPlaceholderText("name@example.com")
        self.email.setAccessibleName("Email address")
        self.date_of_birth = QDateEdit()
        self.date_of_birth.setAccessibleName("Date of birth")
        self.date_of_birth.setCalendarPopup(True)
        self.date_of_birth.setDisplayFormat("dd/MM/yyyy")
        self.date_of_birth.setMinimumDate(NULL_DATE)
        self.date_of_birth.setSpecialValueText("Not set")
        self.date_of_birth.setMaximumDate(QDate.currentDate())
        self.date_of_birth.setDate(NULL_DATE)
        self.gender = QComboBox()
        self.gender.setAccessibleName("Gender")
        self.gender.addItem("Not set", None)
        for gender in ("MALE", "FEMALE", "OTHER"):
            self.gender.addItem(gender.title(), gender)
        self.address = QTextEdit()
        self.address.setAccessibleName("Address")
        self.address.setMaximumHeight(88)
        self.address.setPlaceholderText("Street, district, city")
        self.address.setTabChangesFocus(True)

        account_title = QLabel("Account")
        account_title.setObjectName("sectionTitle")
        card_layout.addWidget(account_title)
        account_grid = QGridLayout()
        account_grid.setHorizontalSpacing(14)
        account_grid.setVerticalSpacing(12)
        self._add_field(account_grid, 0, 0, "Username *", self.username, 2)
        self._add_field(account_grid, 1, 0, "Password *", self.password)
        self._add_field(
            account_grid,
            1,
            1,
            "Confirm password *",
            self.confirm_password,
        )
        account_grid.setColumnStretch(0, 1)
        account_grid.setColumnStretch(1, 1)
        card_layout.addLayout(account_grid)

        personal_title = QLabel("Personal information")
        personal_title.setObjectName("sectionTitle")
        card_layout.addWidget(personal_title)
        personal_grid = QGridLayout()
        personal_grid.setHorizontalSpacing(14)
        personal_grid.setVerticalSpacing(12)
        self._add_field(personal_grid, 0, 0, "Full name *", self.full_name, 2)
        self._add_field(personal_grid, 1, 0, "Phone", self.phone)
        self._add_field(personal_grid, 1, 1, "Email", self.email)
        self._add_field(personal_grid, 2, 0, "Date of birth", self.date_of_birth)
        self._add_field(personal_grid, 2, 1, "Gender", self.gender)
        self._add_field(personal_grid, 3, 0, "Address", self.address, 2)
        personal_grid.setColumnStretch(0, 1)
        personal_grid.setColumnStretch(1, 1)
        card_layout.addLayout(personal_grid)
        card_layout.addWidget(self.loading)

        actions = QHBoxLayout()
        self.back_button = QPushButton("Back to login")
        self.back_button.setObjectName("secondaryButton")
        self.register_button = QPushButton("Create account")
        self.register_button.setObjectName("primaryButton")
        self.register_button.setMinimumWidth(160)
        self.register_button.setAccessibleName("Create patient account")
        actions.addWidget(self.back_button)
        actions.addStretch()
        actions.addWidget(self.register_button)
        card_layout.addLayout(actions)

        outer.addWidget(card)
        outer.addStretch()
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
        QWidget.setTabOrder(self.address, self.back_button)
        QWidget.setTabOrder(self.back_button, self.register_button)

    @staticmethod
    def _add_field(
        layout: QGridLayout,
        row: int,
        column: int,
        label: str,
        field: QWidget,
        column_span: int = 1,
    ) -> None:
        wrapper = QWidget()
        field_layout = QVBoxLayout(wrapper)
        field_layout.setContentsMargins(0, 0, 0, 0)
        field_layout.setSpacing(6)
        field_label = QLabel(label)
        field_label.setObjectName("fieldLabel")
        field_label.setBuddy(field)
        field_layout.addWidget(field_label)
        field_layout.addWidget(field)
        layout.addWidget(wrapper, row, column, 1, column_span)

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

        self.run_api_task(
            "register",
            lambda: self.api_client.post("/api/v1/auth/register", json=payload),
            registered,
            controls=self._form_controls,
            loading_text="Creating account…",
            expire_on_401=False,
        )

    def _show_validation(self, message: str) -> None:
        field: QWidget
        if message.startswith("Username"):
            field = self.username
        elif message.startswith("Password must"):
            field = self.password
        elif message.startswith("Passwords"):
            field = self.confirm_password
        elif message.startswith("Full name"):
            field = self.full_name
        elif message.startswith("Enter a valid email"):
            field = self.email
        elif message.startswith("Phone"):
            field = self.phone
        else:
            field = self.address
        field.setProperty("error", True)
        field.style().unpolish(field)
        field.style().polish(field)
        field.setFocus()
        self.feedback.show_message("Check your details", message, severity="error")

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
            return "Username is required."
        if len(str(payload["password"])) < 8:
            return "Password must be at least 8 characters."
        if payload["password"] != payload["confirm_password"]:
            return "Passwords do not match."
        if not payload["full_name"]:
            return "Full name is required."
        email = payload["email"]
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", str(email)):
            return "Enter a valid email address."
        phone = payload["phone"]
        if phone and not re.fullmatch(r"\+?\d{7,14}", str(phone)):
            return "Phone must contain 7 to 14 digits, optionally prefixed by +."
        if len(str(payload["address"] or "")) > 255:
            return "Address must be 255 characters or fewer."
        return None

    def _clear_form(self) -> None:
        for field in (
            self.username,
            self.password,
            self.confirm_password,
            self.full_name,
            self.phone,
            self.email,
        ):
            field.clear()
        self.address.clear()
        self.date_of_birth.setDate(NULL_DATE)
        self.gender.setCurrentIndex(0)
        self._clear_errors()

    def clear_data(self) -> None:
        """Remove credentials and personal data when leaving registration."""

        self._clear_form()
