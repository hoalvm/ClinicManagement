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

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def current_user(self) -> dict[str, Any] | None:
        return self._current_user

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
        self.cleared.emit()
