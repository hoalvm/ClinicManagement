"""Reusable loading/content/empty/error state coordinator."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from frontend.core.i18n import t
from frontend.ui.design_system import ViewState
from frontend.widgets.empty_state import EmptyState
from frontend.widgets.loading_indicator import LoadingIndicator


class StateHost(QWidget):
    """Render exactly one explicit view state at a time."""

    retry_requested = Signal()
    empty_action_requested = Signal()
    state_changed = Signal(str)

    def __init__(
        self,
        content: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("stateHost")
        self.setProperty("uiSurface", "transparent")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.stack.setObjectName("stateStack")
        root.addWidget(self.stack)

        self.content_widget = content or QWidget()
        self.content_widget.setObjectName(self.content_widget.objectName() or "stateContent")

        self.loading_page = QWidget()
        loading_layout = QVBoxLayout(self.loading_page)
        loading_layout.setContentsMargins(24, 24, 24, 24)
        loading_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.loading = LoadingIndicator(parent=self.loading_page)
        loading_layout.addWidget(self.loading, 0, Qt.AlignmentFlag.AlignCenter)

        self.empty = EmptyState(t("state_empty_title"))
        self.empty.action_requested.connect(self.empty_action_requested)
        self.error = EmptyState(
            t("state_error_title"),
            t("state_error_description"),
            action_text=t("btn_retry"),
        )
        self.error.setProperty("stateRole", "error")
        self.error.action_requested.connect(self.retry_requested)

        self._pages = {
            ViewState.CONTENT: self.content_widget,
            ViewState.LOADING: self.loading_page,
            ViewState.EMPTY: self.empty,
            ViewState.ERROR: self.error,
        }
        for page in self._pages.values():
            self.stack.addWidget(page)

        self._state = ViewState.CONTENT
        self.stack.setCurrentWidget(self.content_widget)

    @property
    def state(self) -> ViewState:
        return self._state

    def set_content(self, content: QWidget) -> None:
        """Replace the content page without changing the current state."""

        if content is self.content_widget:
            return
        was_content = self._state is ViewState.CONTENT
        previous = self.content_widget
        self.stack.removeWidget(previous)
        previous.setParent(None)
        self.content_widget = content
        self._pages[ViewState.CONTENT] = content
        self.stack.insertWidget(0, content)
        if was_content:
            self.stack.setCurrentWidget(content)

    def set_state(self, state: ViewState | str) -> None:
        resolved = ViewState.coerce(state)
        if resolved is self._state and self.stack.currentWidget() is self._pages[resolved]:
            return
        self.loading.stop()
        self._state = resolved
        self.setProperty("viewState", resolved.value)
        self.stack.setCurrentWidget(self._pages[resolved])
        if resolved is ViewState.LOADING:
            self.loading.start()
        self.state_changed.emit(resolved.value)

    def show_content(self) -> None:
        self.set_state(ViewState.CONTENT)

    def show_loading(self, text: str | None = None) -> None:
        self.set_state(ViewState.LOADING)
        self.loading.start(text or t("loading"))

    def show_empty(
        self,
        title: str | None = None,
        description: str | None = None,
        *,
        action_text: str | None = None,
    ) -> None:
        self.empty.set_title(title or t("state_empty_title"))
        self.empty.set_description(description)
        self.empty.set_action(action_text)
        self.set_state(ViewState.EMPTY)

    def show_error(
        self,
        title: str | None = None,
        description: str | None = None,
        *,
        retry_text: str | None = None,
    ) -> None:
        self.error.set_title(title or t("state_error_title"))
        self.error.set_description(description or t("state_error_description"))
        self.error.set_action(retry_text or t("btn_retry"))
        self.set_state(ViewState.ERROR)


__all__ = ["StateHost"]
