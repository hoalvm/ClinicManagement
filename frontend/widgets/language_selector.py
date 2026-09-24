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
            self.label = QLabel("🌐 Ngôn ngữ:")
            self.label.setStyleSheet("color: #64748b; font-size: 12px; font-weight: 600;")
            layout.addWidget(self.label)
        else:
            self.label = None

        self.combo = QComboBox(self)
        self.combo.setObjectName("languageCombo")
        self.combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.combo.setMinimumHeight(32)
        self.combo.setStyleSheet(
            "QComboBox#languageCombo { "
            "   background: #ffffff; "
            "   border: 1px solid #cbd5e1; "
            "   border-radius: 6px; "
            "   padding: 4px 10px; "
            "   font-size: 12px; "
            "   font-weight: 600; "
            "   color: #1e293b; "
            "} "
            "QComboBox#languageCombo:hover { "
            "   border-color: #0f766e; "
            "   background: #f8fafc; "
            "} "
            "QComboBox#languageCombo::drop-down { "
            "   border: none; "
            "   width: 20px; "
            "} "
            "QComboBox#languageCombo QAbstractItemView { "
            "   background-color: #ffffff; "
            "   color: #0f172a; "
            "   border: 1px solid #cbd5e1; "
            "   border-radius: 6px; "
            "   padding: 2px; "
            "   outline: none; "
            "   selection-background-color: #e6fffa; "
            "   selection-color: #0f766e; "
            "} "
            "QComboBox#languageCombo QAbstractItemView::item { "
            "   background-color: #ffffff; "
            "   color: #0f172a; "
            "   min-height: 28px; "
            "   padding: 5px 8px; "
            "   font-size: 12px; "
            "   font-weight: 600; "
            "} "
            "QComboBox#languageCombo QAbstractItemView::item:hover, "
            "QComboBox#languageCombo QAbstractItemView::item:selected { "
            "   background-color: #e6fffa; "
            "   color: #0f766e; "
            "   font-weight: 700; "
            "}"
        )

        self.combo.addItem("🇻🇳 Tiếng Việt", "vi")
        self.combo.addItem("🇬🇧 English", "en")

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
            self.label.setText("🌐 " + ("Ngôn ngữ:" if current == "vi" else "Language:"))

    def _on_selection_changed(self, index: int) -> None:
        lang = self.combo.itemData(index)
        if lang:
            self._i18n.set_language(lang)

    def _on_global_language_changed(self, _lang: str) -> None:
        self._sync_to_current_language()
