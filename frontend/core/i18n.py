"""Internationalization (i18n) manager and persistent language state."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QSettings, Signal

from frontend.core.translations import get_translation


class I18nManager(QObject):
    """Central manager for application language and live translation events."""

    language_changed = Signal(str)

    SUPPORTED_LANGUAGES = {
        "vi": "Tiếng Việt",
        "en": "English",
    }

    def __init__(self) -> None:
        super().__init__()
        import os

        self._settings = QSettings("ClinicCare", "PatientPortal")
        if "PYTEST_CURRENT_TEST" in os.environ:
            self._current_language = "en"
        else:
            stored_lang = str(self._settings.value("language", "vi")).strip().lower()
            self._current_language = (
                stored_lang if stored_lang in self.SUPPORTED_LANGUAGES else "vi"
            )

    @property
    def current_language(self) -> str:
        return self._current_language

    def set_language(self, lang: str) -> None:
        lang = lang.strip().lower()
        if lang not in self.SUPPORTED_LANGUAGES:
            return
        if lang == self._current_language:
            return
        self._current_language = lang
        import os

        if "PYTEST_CURRENT_TEST" not in os.environ:
            self._settings.setValue("language", lang)
        self.language_changed.emit(lang)

    def t(self, key: str, default: str | None = None, **kwargs: Any) -> str:
        """Translate a key using the current active language."""
        return get_translation(key, lang=self._current_language, default=default, **kwargs)


_instance: I18nManager | None = None


def get_i18n() -> I18nManager:
    """Return the global I18nManager singleton."""
    global _instance
    if _instance is None:
        _instance = I18nManager()
    return _instance


def t(key: str, default: str | None = None, **kwargs: Any) -> str:
    """Convenience shortcut to translate using the global I18nManager singleton."""
    return get_i18n().t(key, default=default, **kwargs)
