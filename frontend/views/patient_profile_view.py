"""Read and edit the authenticated patient's profile."""

from __future__ import annotations

import re
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QFrame,
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
from frontend.core.session import SessionState
from frontend.views.common import BaseApiView, require_dict
from frontend.widgets.page_header import PageHeader

NULL_DATE = QDate(1752, 9, 14)


class PatientProfileView(BaseApiView):
    profile_updated = Signal(object)

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
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        self.header = PageHeader(
            t("profile_title"),
            t("profile_subtitle"),
        )
        root.addWidget(self.header)
        root.addWidget(self.feedback)
        root.addWidget(self.loading)

        scroll = QScrollArea()
        scroll.setObjectName("pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAccessibleName("Patient profile")
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 2, 8, 4)
        content_layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("profileHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(22, 18, 22, 18)
        hero_layout.setSpacing(16)

        avatar = QFrame()
        avatar.setObjectName("profileAvatar")
        avatar.setFixedSize(58, 58)
        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        self.avatar_text = QLabel("P")
        self.avatar_text.setObjectName("profileAvatarText")
        self.avatar_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_text.setAccessibleName("Patient initials")
        avatar_layout.addWidget(self.avatar_text)
        hero_layout.addWidget(avatar)

        identity = QVBoxLayout()
        identity.setSpacing(3)
        self.hero_name = QLabel("Patient")
        self.hero_name.setObjectName("sectionTitle")
        self.hero_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.hero_username = QLabel(t("account_notice"))
        self.hero_username.setObjectName("mutedLabel")
        self.hero_username.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        identity.addWidget(self.hero_name)
        identity.addWidget(self.hero_username)
        hero_layout.addLayout(identity, 1)

        self.edit_button = QPushButton(t("btn_edit"))
        self.edit_button.setObjectName("secondaryButton")
        hero_layout.addWidget(self.edit_button, 0, Qt.AlignmentFlag.AlignVCenter)
        content_layout.addWidget(hero)

        card = QFrame()
        card.setObjectName("contentCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 22, 24, 22)
        card_layout.setSpacing(16)

        self.username = QLineEdit()
        self.username.setReadOnly(True)
        self.username.setAccessibleName("Username")
        self.full_name = QLineEdit()
        self.full_name.setMaxLength(100)
        self.full_name.setAccessibleName("Full name")
        self.phone = QLineEdit()
        self.phone.setMaxLength(15)
        self.phone.setAccessibleName("Phone number")
        self.email = QLineEdit()
        self.email.setMaxLength(100)
        self.email.setAccessibleName("Email address")
        self.date_of_birth = QDateEdit()
        self.date_of_birth.setCalendarPopup(True)
        self.date_of_birth.setDisplayFormat("dd/MM/yyyy")
        self.date_of_birth.setMinimumDate(NULL_DATE)
        self.date_of_birth.setSpecialValueText(t("not_set"))
        self.date_of_birth.setMaximumDate(QDate.currentDate())
        self.date_of_birth.setAccessibleName("Date of birth")
        self.gender = QComboBox()
        self._populate_gender_combo()
        self.gender.setAccessibleName("Gender")
        self.address = QTextEdit()
        self.address.setMaximumHeight(96)
        self.address.setAccessibleName("Address")
        self.address.setTabChangesFocus(True)

        self._form_labels: dict[str, QLabel] = {}
        self.personal_title = QLabel(t("sec_personal_info"))
        self.personal_title.setObjectName("sectionTitle")
        card_layout.addWidget(self.personal_title)
        personal_form = self._form_layout()
        self._add_form_row(personal_form, "username", self.username)
        self._add_form_row(personal_form, "full_name", self.full_name)
        self._add_form_row(personal_form, "date_of_birth", self.date_of_birth)
        self._add_form_row(personal_form, "gender", self.gender)
        card_layout.addLayout(personal_form)

        self.contact_title = QLabel(t("sec_contact_info"))
        self.contact_title.setObjectName("sectionTitle")
        card_layout.addWidget(self.contact_title)
        contact_form = self._form_layout()
        self._add_form_row(contact_form, "phone", self.phone)
        self._add_form_row(contact_form, "email", self.email)
        self._add_form_row(contact_form, "address", self.address)
        card_layout.addLayout(contact_form)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addStretch()
        self.cancel_button = QPushButton(t("btn_cancel_action"))
        self.cancel_button.setObjectName("secondaryButton")
        self.cancel_button.setAccessibleName("Cancel profile changes")
        self.save_button = QPushButton(t("btn_save"))
        self.save_button.setObjectName("primaryButton")
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.save_button)
        card_layout.addLayout(actions)
        content_layout.addWidget(card)
        content_layout.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        self._editable = (
            self.full_name,
            self.phone,
            self.email,
            self.date_of_birth,
            self.gender,
            self.address,
        )
        self.edit_button.clicked.connect(lambda: self._set_editing(True, focus=True))
        self.cancel_button.clicked.connect(self._cancel)
        self.save_button.clicked.connect(self._save)
        self._set_editing(False)

        get_i18n().language_changed.connect(self.retranslate_ui)

    def _populate_gender_combo(self) -> None:
        curr = self.gender.currentData()
        self.gender.blockSignals(True)
        self.gender.clear()
        self.gender.addItem(t("not_set"), None)
        for g_code, g_key in [("MALE", "gender_male"), ("FEMALE", "gender_female"), ("OTHER", "gender_other")]:
            self.gender.addItem(t(g_key), g_code)
        idx = self.gender.findData(curr)
        if idx >= 0:
            self.gender.setCurrentIndex(idx)
        self.gender.blockSignals(False)

    def retranslate_ui(self) -> None:
        """Update all text in PatientProfileView according to current language."""
        self.header.set_title(t("profile_title"))
        self.header.set_subtitle(t("profile_subtitle"))
        self.edit_button.setText(t("btn_edit"))
        self.cancel_button.setText(t("btn_cancel_action"))
        self.save_button.setText(t("btn_save"))
        self.personal_title.setText(t("sec_personal_info"))
        self.contact_title.setText(t("sec_contact_info"))
        self.date_of_birth.setSpecialValueText(t("not_set"))
        self._populate_gender_combo()
        for key, lbl in self._form_labels.items():
            lbl.setText(t(key))
        if not self.username.text():
            self.hero_username.setText(t("account_notice"))

    @staticmethod
    def _form_layout() -> QFormLayout:
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setHorizontalSpacing(28)
        form.setVerticalSpacing(13)
        return form

    def _add_form_row(self, form: QFormLayout, key: str, field: QWidget) -> None:
        label = QLabel(t(key))
        label.setObjectName("fieldLabel")
        label.setBuddy(field)
        self._form_labels[key] = label
        form.addRow(label, field)

    def activate(self) -> None:
        self.load()

    def load(self) -> None:
        self.run_api_task(
            "profile",
            lambda: self.api_client.get("/api/v1/patients/me"),
            self._render,
            controls=(self.edit_button, *self._editable),
            loading_text=t("loading"),
            on_finished=lambda: self._set_editing(False),
        )

    def _render(self, payload: object) -> None:
        data = require_dict(payload)
        self._profile = dict(data)
        username = str(data.get("username") or "")
        full_name = str(data.get("full_name") or "")
        self.username.setText(username)
        self.full_name.setText(full_name)
        self.phone.setText(str(data.get("phone") or ""))
        self.email.setText(str(data.get("email") or ""))
        parsed_date = QDate.fromString(str(data.get("date_of_birth") or ""), "yyyy-MM-dd")
        self.date_of_birth.setDate(parsed_date if parsed_date.isValid() else NULL_DATE)
        gender = str(data.get("gender") or "")
        index = self.gender.findData(gender) if gender else 0
        if index < 0 and gender:
            self.gender.addItem(gender.title(), gender)
            index = self.gender.findData(gender)
        self.gender.setCurrentIndex(max(0, index))
        self.address.setPlainText(str(data.get("address") or ""))
        self._update_identity(full_name, username)
        current_user = self.session.current_user or {}
        merged_user = {**current_user, **data}
        self.session.update_current_user(merged_user)
        self.profile_updated.emit(dict(merged_user))
        self._clear_validation()
        self._set_editing(False)

    def _update_identity(self, full_name: str, username: str) -> None:
        display_name = full_name or username or "Patient"
        initials = "".join(part[0] for part in display_name.split() if part)[:2].upper() or "P"
        self.avatar_text.setText(initials)
        self.hero_name.setText(display_name)
        self.hero_username.setText(f"@{username}" if username else t("account_notice"))

    def _set_editing(self, editing: bool, *, focus: bool = False) -> None:
        for widget in (self.full_name, self.phone, self.email, self.address):
            widget.setReadOnly(not editing)
            self._refresh_property(widget, "viewMode", not editing)
        self.date_of_birth.setReadOnly(not editing)
        self._refresh_property(self.date_of_birth, "viewMode", not editing)
        self.gender.setEnabled(editing)
        self._refresh_property(self.gender, "viewMode", not editing)
        self._refresh_property(self.username, "viewMode", True)
        self.edit_button.setVisible(not editing)
        self.save_button.setVisible(editing)
        self.cancel_button.setVisible(editing)
        if editing and focus:
            self.feedback.clear()
            self.full_name.setFocus(Qt.FocusReason.ShortcutFocusReason)
            self.full_name.selectAll()

    @staticmethod
    def _refresh_property(widget: QWidget, name: str, value: object) -> None:
        widget.setProperty(name, value)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _cancel(self) -> None:
        self.feedback.clear()
        if self._profile:
            self._render(self._profile)
        else:
            self._set_editing(False)

    def _clear_validation(self) -> None:
        for widget in self._editable:
            self._refresh_property(widget, "error", False)

    def _validation_error(self, widget: QWidget, message: str) -> None:
        self._refresh_property(widget, "error", True)
        self.feedback.show_message("Check your details", message, severity="error")
        widget.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _save(self) -> None:
        self._clear_validation()
        full_name = self.full_name.text().strip()
        email = self.email.text().strip()
        phone = self.phone.text().strip()
        if not full_name:
            self._validation_error(self.full_name, "Full name is required.")
            return
        if email and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            self._validation_error(self.email, "Enter a valid email address.")
            return
        if phone and not re.fullmatch(r"\+?\d{7,14}", phone):
            self._validation_error(
                self.phone,
                "Phone must contain 7 to 14 digits, optionally prefixed by +.",
            )
            return
        if len(self.address.toPlainText().strip()) > 255:
            self._validation_error(self.address, "Address must be 255 characters or fewer.")
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

        completed = False

        def saved(result: object) -> None:
            nonlocal completed
            completed = True
            self._render(result)
            self.feedback.show_message(
                "Profile updated",
                "Your changes have been saved successfully.",
                severity="success",
            )

        def finished() -> None:
            self._set_editing(not completed)

        self.run_api_task(
            "save-profile",
            save_and_reload,
            saved,
            controls=(self.save_button, self.cancel_button, *self._editable),
            loading_text=t("processing"),
            on_finished=finished,
        )

    def clear_data(self) -> None:
        self._profile = None
        self.feedback.clear()
        self.username.clear()
        self.full_name.clear()
        self.phone.clear()
        self.email.clear()
        self.address.clear()
        self.gender.setCurrentIndex(0)
        self.date_of_birth.setDate(NULL_DATE)
        self._update_identity("", "")
        self._clear_validation()
        self._set_editing(False)
