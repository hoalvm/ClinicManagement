"""In-memory authentication state."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal


class SessionState(QObject):
    """Own the JWT and current user for the lifetime of the process only."""

    authenticated = Signal(dict)
    cleared = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._access_token: str | None = None
        self._current_user: dict[str, Any] | None = None
        self._doctor_profile: dict[str, Any] | None = None

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def current_user(self) -> dict[str, Any] | None:
        return self._current_user

    @property
    def role(self) -> str:
        if self._current_user:
            return str(self._current_user.get("role", "")).upper()
        return ""

    @property
    def username(self) -> str:
        if self._current_user:
            return str(self._current_user.get("username", ""))
        return ""

    @property
    def doctor_profile(self) -> dict[str, Any] | None:
        return self._doctor_profile

    def set_doctor_profile(self, profile: dict[str, Any] | None) -> None:
        self._doctor_profile = dict(profile) if profile else None

    @property
    def is_authenticated(self) -> bool:
        return bool(self._access_token)

    def set_authenticated(self, access_token: str, current_user: dict[str, Any]) -> None:
        self._access_token = access_token
        self._current_user = dict(current_user)
        self.authenticated.emit(dict(current_user))

    def update_current_user(self, current_user: dict[str, Any]) -> None:
        if not self._access_token:
            return
        self._current_user = dict(current_user)

    def clear(self) -> None:
        self._access_token = None
        self._current_user = None
        self._doctor_profile = None
        self.cleared.emit()


# Global shared session instance
session_state = SessionState()

