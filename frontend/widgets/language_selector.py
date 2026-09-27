"""Reusable language selector widget for login view and sidebar navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from frontend.core.i18n import get_i18n


class LanguageSelector(QWidget):
    """Dropdown selector allowing the patient to switch between Vietnamese and English."""

    def __init__(self, parent: QWidget | None = None, *, show_label: bool = False) -> None:
        super().__init__(parent)
        self._i18n = get_i18n()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        if show_label:
            self.label = QLabel("Ngôn ngữ:")
            self.label.setObjectName("languageLabel")
            layout.addWidget(self.label)
        else:
            self.label = None

        self.combo = QComboBox(self)
        self.combo.setObjectName("languageCombo")
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo.setMinimumHeight(32)

        self.combo.addItem("Tiếng Việt", "vi")
        self.combo.addItem("English", "en")

        self._sync_to_current_language()
        self.combo.currentIndexChanged.connect(self._on_selection_changed)
        self._i18n.language_changed.connect(self._on_global_language_changed)

        layout.addWidget(self.combo)

    def _sync_to_current_language(self) -> None:
        current = self._i18n.current_language
        self.combo.blockSignals(True)
        for i in range(self.combo.count()):
            if self.combo.itemData(i) == current:
                self.combo.setCurrentIndex(i)
                break
        self.combo.blockSignals(False)

        if self.label:
            self.label.setText("Ngôn ngữ:" if current == "vi" else "Language:")

    def _on_selection_changed(self, index: int) -> None:
        lang = self.combo.itemData(index)
        if lang:
            self._i18n.set_language(lang)

    def _on_global_language_changed(self, _lang: str) -> None:
        self._sync_to_current_language()
