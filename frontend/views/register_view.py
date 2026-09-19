"""Patient registration screen."""

from __future__ import annotations

import re

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
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
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        outer = QHBoxLayout(container)
        outer.addStretch()

        card = QFrame()
        card.setObjectName("authCard")
        card.setMaximumWidth(650)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 30, 36, 30)
        card_layout.setSpacing(14)
        title = QLabel("Create patient account")
        title.setObjectName("authTitle")
        subtitle = QLabel("Enter your details to access the patient portal.")
        subtitle.setObjectName("mutedLabel")
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(12)
        self.username = QLineEdit()
        self.username.setMaxLength(50)
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password = QLineEdit()
        self.confirm_password.setMaxLength(128)
        self.confirm_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.full_name = QLineEdit()
        self.full_name.setMaxLength(100)
        self.phone = QLineEdit()
        self.phone.setMaxLength(15)
        self.email = QLineEdit()
        self.email.setMaxLength(100)
        self.date_of_birth = QDateEdit()
        self.date_of_birth.setCalendarPopup(True)
        self.date_of_birth.setDisplayFormat("dd/MM/yyyy")
        self.date_of_birth.setMinimumDate(NULL_DATE)
        self.date_of_birth.setSpecialValueText("Not set")
        self.date_of_birth.setMaximumDate(QDate.currentDate())
        self.date_of_birth.setDate(NULL_DATE)
        self.gender = QComboBox()
        self.gender.addItem("Not set", None)
        for gender in ("MALE", "FEMALE", "OTHER"):
            self.gender.addItem(gender, gender)
        self.address = QTextEdit()
        self.address.setMaximumHeight(86)
        self.address.setPlaceholderText("Street, district, city")

        form.addRow("Username *", self.username)
        form.addRow("Password *", self.password)
        form.addRow("Confirm Password *", self.confirm_password)
        form.addRow("Full Name *", self.full_name)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Date of Birth", self.date_of_birth)
        form.addRow("Gender", self.gender)
        form.addRow("Address", self.address)
        card_layout.addLayout(form)
        card_layout.addWidget(self.loading)

        actions = QHBoxLayout()
        self.back_button = QPushButton("Back to Login")
        self.back_button.setObjectName("secondaryButton")
        self.register_button = QPushButton("Register")
        self.register_button.setObjectName("primaryButton")
        actions.addWidget(self.back_button)
        actions.addStretch()
        actions.addWidget(self.register_button)
        card_layout.addLayout(actions)

        outer.addWidget(card)
        outer.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

        self.back_button.clicked.connect(self.back_requested)
        self.register_button.clicked.connect(self._register)
        self.confirm_password.returnPressed.connect(self._register)

    def _register(self) -> None:
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
            QMessageBox.warning(self, "Registration", validation)
            return

        username = str(payload["username"])

        def registered(_result: object) -> None:
            QMessageBox.information(
                self,
                "Registration complete",
                "Your patient account was created. You can now sign in.",
            )
            self._clear_form()
            self.registration_succeeded.emit(username)

        self.run_api_task(
            "register",
            lambda: self.api_client.post("/api/v1/auth/register", json=payload),
            registered,
            controls=(self.register_button, self.back_button),
            loading_text="Creating account…",
            expire_on_401=False,
        )

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

    def clear_data(self) -> None:
        """Remove credentials and personal data when leaving registration."""

        self._clear_form()
