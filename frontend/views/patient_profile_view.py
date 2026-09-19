"""Read and edit the authenticated patient's profile."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QDate
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.api.api_client import ApiClient
from frontend.core.session import SessionState
from frontend.views.common import BaseApiView, require_dict

NULL_DATE = QDate(1752, 9, 14)


class PatientProfileView(BaseApiView):
    def __init__(
        self,
        api_client: ApiClient,
        session: SessionState,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(api_client, parent)
        self.session = session
        self._profile: dict[str, Any] | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)
        title = QLabel("My Profile")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        root.addWidget(self.loading)

        card = QFrame()
        card.setObjectName("contentCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        form = QFormLayout()
        form.setHorizontalSpacing(28)
        form.setVerticalSpacing(14)

        self.username = QLineEdit()
        self.username.setReadOnly(True)
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
        self.gender = QComboBox()
        self.gender.addItem("Not set", None)
        for gender in ("MALE", "FEMALE", "OTHER"):
            self.gender.addItem(gender, gender)
        self.address = QTextEdit()
        self.address.setMaximumHeight(100)

        form.addRow("Username", self.username)
        form.addRow("Full Name", self.full_name)
        form.addRow("Phone", self.phone)
        form.addRow("Email", self.email)
        form.addRow("Date of Birth", self.date_of_birth)
        form.addRow("Gender", self.gender)
        form.addRow("Address", self.address)
        card_layout.addLayout(form)

        actions = QHBoxLayout()
        actions.addStretch()
        self.edit_button = QPushButton("Edit")
        self.edit_button.setObjectName("secondaryButton")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("secondaryButton")
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("primaryButton")
        actions.addWidget(self.edit_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)
        card_layout.addLayout(actions)
        root.addWidget(card)
        root.addStretch()

        self._editable = (
            self.full_name,
            self.phone,
            self.email,
            self.date_of_birth,
            self.gender,
            self.address,
        )
        self.edit_button.clicked.connect(lambda: self._set_editing(True))
        self.cancel_button.clicked.connect(self._cancel)
        self.save_button.clicked.connect(self._save)
        self._set_editing(False)

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        self.run_api_task(
            "profile",
            lambda: self.api_client.get("/api/v1/patients/me"),
            self._render,
            controls=(self.edit_button, self.save_button, self.cancel_button),
            loading_text="Loading profile…",
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        self._profile = dict(data)
        self.username.setText(str(data.get("username") or ""))
        self.full_name.setText(str(data.get("full_name") or ""))
        self.phone.setText(str(data.get("phone") or ""))
        self.email.setText(str(data.get("email") or ""))
        parsed_date = QDate.fromString(str(data.get("date_of_birth") or ""), "yyyy-MM-dd")
        self.date_of_birth.setDate(parsed_date if parsed_date.isValid() else NULL_DATE)
        gender = str(data.get("gender") or "")
        index = self.gender.findData(gender) if gender else 0
        if index < 0 and gender:
            self.gender.addItem(gender, gender)
            index = self.gender.findData(gender)
        self.gender.setCurrentIndex(max(0, index))
        self.address.setPlainText(str(data.get("address") or ""))
        current_user = self.session.current_user or {}
        self.session.update_current_user({**current_user, **data})
        self._set_editing(False)

    def _set_editing(self, editing: bool) -> None:
        for widget in self._editable:
            widget.setEnabled(editing)
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)

    def _cancel(self) -> None:
        if self._profile:
            self._render(self._profile)
        else:
            self._set_editing(False)

    def _save(self) -> None:
        full_name = self.full_name.text().strip()
        email = self.email.text().strip()
        phone = self.phone.text().strip()
        if not full_name:
            QMessageBox.warning(self, "Profile", "Full name is required.")
            return
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            QMessageBox.warning(self, "Profile", "Enter a valid email address.")
            return
        if phone and not re.fullmatch(r"\+?\d{7,14}", phone):
            QMessageBox.warning(
                self,
                "Profile",
                "Phone must contain 7 to 14 digits, optionally prefixed by +.",
            )
            return
        if len(self.address.toPlainText().strip()) > 255:
            QMessageBox.warning(self, "Profile", "Address must be 255 characters or fewer.")
            return

        selected_date = self.date_of_birth.date()
        payload: dict[str, Any] = {
            "full_name": full_name,
            "phone": phone or None,
            "email": email or None,
            "date_of_birth": (
                None if selected_date == NULL_DATE else selected_date.toString("yyyy-MM-dd")
            ),
            "gender": self.gender.currentData(),
            "address": self.address.toPlainText().strip() or None,
        }

        def save_and_reload() -> object:
            self.api_client.patch("/api/v1/patients/me", json=payload)
            return self.api_client.get("/api/v1/patients/me")

        def saved(result: object) -> None:
            self._render(result)
            QMessageBox.information(self, "Profile", "Your profile was saved.")

        self.run_api_task(
            "save-profile",
            save_and_reload,
            saved,
            controls=(self.save_button, self.cancel_button),
            loading_text="Saving profile…",
        )

    def clear_data(self) -> None:
        self._profile = None
        self.username.clear()
        self.full_name.clear()
        self.phone.clear()
        self.email.clear()
        self.address.clear()
        self.gender.setCurrentIndex(0)
        self.date_of_birth.setDate(NULL_DATE)
        self._set_editing(False)
