"""Shared asynchronous lifecycle and list-first UI helpers for Admin pages."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from PySide6.QtCore import QObject, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from frontend.api.workers import ApiWorker
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.form_field import FormField
from frontend.widgets.loading_indicator import LoadingIndicator
from frontend.widgets.state_host import StateHost
from frontend.widgets.table_actions import RowAction, TableActionMenu


def connect_action(
    signal: object,
    callback: Callable[[], None],
) -> None:
    """Connect a Qt signal that may emit a ``checked: bool`` to a zero-arg callback.

    ``QPushButton.clicked``, ``QToolButton.clicked``, and ``QAction.triggered``
    all pass an extra boolean argument.  Wrapping the callback here ensures the
    value is discarded unconditionally, so lambdas that capture a row dictionary
    via ``lambda item=item: ...`` never receive ``False`` as their first argument.
    """
    signal.connect(lambda _checked=False, _cb=callback: _cb())



class AdminApiError(RuntimeError):
    """A normalized failure returned by the legacy Admin API adapter."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def require_success(response: Any, default_message: str) -> Any:
    """Return a successful legacy response or raise a user-facing error.

    Admin still uses the requests-compatible API adapter while the patient
    portal uses the newer typed client.  Keeping response validation in the
    worker means HTTP parsing and error normalization never block the UI
    thread and every Admin page follows the same rule.
    """

    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int) and 200 <= status_code < 300:
        return response

    message = default_message
    try:
        payload = response.json()
        if isinstance(payload, dict) and payload.get("detail"):
            message = str(payload["detail"])
    except (AttributeError, TypeError, ValueError):
        pass
    raise AdminApiError(message, status_code)


class _AdminTaskHandler(QObject):
    """Receive one worker result on the GUI thread and keep callbacks alive."""

    def __init__(
        self,
        page: AdminApiPage,
        key: str,
        on_success: Callable[[Any], None],
        controls: tuple[QWidget, ...],
        on_finished: Callable[[], None] | None,
        on_error: Callable[[Exception], None] | None,
        state_host: StateHost | None,
        empty_when: Callable[[Any], bool] | None,
    ) -> None:
        super().__init__(page)
        self.page = page
        self.key = key
        self.on_success = on_success
        self.controls = controls
        self.on_finished = on_finished
        self.on_error = on_error
        self.state_host = state_host
        self.empty_when = empty_when

    @Slot(object)
    def success(self, result: Any) -> None:
        self.page._admin_task_succeeded(self, result)

    @Slot(object)
    def error(self, error: Exception) -> None:
        self.page._admin_task_failed(self, error)

    @Slot()
    def finished(self) -> None:
        self.page._admin_task_finished(self)


class AdminApiPage(QWidget):
    """Shared non-blocking API lifecycle for Admin pages.

    A stable task key prevents accidental double submission.  Only controls
    participating in that request are disabled, so the rest of the window can
    still repaint and remain navigable during a slow request.
    """

    session_expired = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.feedback = FeedbackBanner(self)
        self.loading = LoadingIndicator(parent=self)
        self._admin_workers: dict[str, ApiWorker] = {}
        self._admin_handlers: dict[str, _AdminTaskHandler] = {}
        self.state_host: StateHost | None = None
        self._state_empty_title = "Chưa có dữ liệu"
        self._state_empty_description = "Chưa có dữ liệu để hiển thị."
        self._state_empty_action_text: str | None = None

    def add_request_feedback(self, layout: QVBoxLayout) -> None:
        """Place shared feedback widgets directly below a page header."""

        layout.addWidget(self.feedback)
        layout.addWidget(self.loading)

    def bind_state_host(
        self,
        content: QWidget,
        retry: Callable[[], Any],
        *,
        empty_title: str,
        empty_description: str,
        empty_action_text: str | None = None,
        on_empty_action: Callable[[], Any] | None = None,
    ) -> StateHost:
        """Wrap a page's principal content in the shared four-state host.

        Admin CRUD forms remain available while the list/statistics area moves
        independently between loading, content, empty and error states.  This
        keeps an empty response visibly different from a failed request and
        gives every load error the same in-place retry behaviour.
        """

        host = StateHost(content, self)
        host.setAccessibleName(f"Trạng thái {content.accessibleName() or 'nội dung quản trị'}")
        host.retry_requested.connect(retry)
        if on_empty_action is not None:
            host.empty_action_requested.connect(on_empty_action)
        self.state_host = host
        self._state_empty_title = empty_title
        self._state_empty_description = empty_description
        self._state_empty_action_text = empty_action_text
        return host

    def run_admin_task(
        self,
        key: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        *,
        controls: Iterable[QWidget] = (),
        loading_text: str = "Đang tải…",
        on_finished: Callable[[], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
        clear_feedback: bool = True,
        stateful: bool = False,
        empty_when: Callable[[Any], bool] | None = None,
    ) -> bool:
        """Start one keyed request and return ``False`` when it is a duplicate."""

        if key in self._admin_workers:
            return False

        controlled_widgets = tuple(controls)
        for widget in controlled_widgets:
            widget.setEnabled(False)
        if clear_feedback:
            self.feedback.clear()
        state_host = self.state_host if stateful else None
        if state_host is not None:
            state_host.show_loading(loading_text)
        else:
            self.loading.start(loading_text)

        worker = ApiWorker(operation)
        handler = _AdminTaskHandler(
            self,
            key,
            on_success,
            controlled_widgets,
            on_finished,
            on_error,
            state_host,
            empty_when,
        )
        self._admin_workers[key] = worker
        self._admin_handlers[key] = handler
        worker.signals.success.connect(handler.success)
        worker.signals.error.connect(handler.error)
        worker.signals.finished.connect(handler.finished)
        QThreadPool.globalInstance().start(worker)
        return True

    def _admin_task_succeeded(self, handler: _AdminTaskHandler, result: Any) -> None:
        try:
            handler.on_success(result)
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            self._admin_task_failed(handler, error)
            return

        if handler.state_host is not None:
            is_empty = handler.empty_when(result) if handler.empty_when else False
            if is_empty:
                handler.state_host.show_empty(
                    self._state_empty_title,
                    self._state_empty_description,
                    action_text=self._state_empty_action_text,
                )
            else:
                handler.state_host.show_content()

    @staticmethod
    def error_message(error: Exception) -> str:
        """Return a safe Vietnamese message for a worker exception."""

        if isinstance(error, AdminApiError):
            return error.message
        return "Đã xảy ra lỗi không mong muốn. Vui lòng thử lại."

    def _admin_task_failed(self, handler: _AdminTaskHandler, error: Exception) -> None:
        if isinstance(error, AdminApiError) and error.status_code == 401:
            self.session_expired.emit()
            return
        if handler.on_error is not None:
            handler.on_error(error)
            return
        if handler.state_host is not None:
            handler.state_host.show_error(
                "Không thể tải dữ liệu",
                self.error_message(error),
                retry_text="Thử lại",
            )
            return
        self.feedback.show_message(
            "Không thể hoàn tất yêu cầu",
            self.error_message(error),
            severity="error",
        )

    def _admin_task_finished(self, handler: _AdminTaskHandler) -> None:
        self._admin_workers.pop(handler.key, None)
        self._admin_handlers.pop(handler.key, None)
        for widget in handler.controls:
            try:
                widget.setEnabled(True)
            except RuntimeError:
                # A modal dialog may have been closed while its request ended.
                pass
        if not any(item.state_host is None for item in self._admin_handlers.values()):
            self.loading.stop()
        if handler.on_finished is not None:
            handler.on_finished()
        handler.deleteLater()

    def has_pending_task(self, key: str) -> bool:
        return key in self._admin_workers


class AdminSearchBar(FilterToolbar):
    """Compatibility facade over the shared responsive filter toolbar."""

    def __init__(
        self,
        placeholder: str,
        parent: QWidget | None = None,
        *,
        delay_ms: int = 350,
    ) -> None:
        super().__init__(
            placeholder,
            parent,
            debounce_ms=delay_ms,
            clear_text="Xóa bộ lọc",
            search_accessible_name=placeholder,
        )
        self.input = self.search_input

    @property
    def text(self) -> str:
        return self.search_input.text().strip()


class AdminFormDialog(QDialog):
    """Responsive two-column form dialog shared by Admin create/edit flows."""

    COMPACT_BREAKPOINT = 620

    def __init__(
        self,
        title: str,
        subtitle: str,
        parent: QWidget | None = None,
        *,
        save_text: str = "Lưu",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("adminFormDialog")
        self.setWindowTitle(title)
        self.setMinimumWidth(520)
        self.resize(680, 360)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        heading.setAccessibleName(title)
        root.addWidget(heading)
        supporting = QLabel(subtitle)
        supporting.setObjectName("mutedLabel")
        supporting.setWordWrap(True)
        root.addWidget(supporting)

        self.feedback = FeedbackBanner(self)
        root.addWidget(self.feedback)
        self.form_scroll = QScrollArea()
        self.form_scroll.setWidgetResizable(True)
        self.form_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.form_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.form_scroll.setProperty("uiSurface", "transparent")
        self.form_content = QWidget()
        self.form_content.setProperty("uiSurface", "transparent")
        self.fields_layout = QGridLayout(self.form_content)
        self.fields_layout.setContentsMargins(0, 2, 0, 0)
        self.fields_layout.setHorizontalSpacing(14)
        self.fields_layout.setVerticalSpacing(10)
        self.fields_layout.setColumnStretch(0, 1)
        self.fields_layout.setColumnStretch(1, 1)
        self.form_scroll.setWidget(self.form_content)
        root.addWidget(self.form_scroll, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self.save_button.setText(save_text)
        self.save_button.setObjectName("primaryButton")
        self.cancel_button.setText("Hủy")
        self.cancel_button.setObjectName("secondaryButton")
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)
        self.fields: list[FormField] = []
        self._field_positions: list[tuple[int, int, int]] = []
        self._enabled_before_busy: dict[QWidget, bool] = {}
        self._compact_fields = False

    def add_field(
        self,
        label: str,
        control: QWidget,
        row: int,
        column: int = 0,
        *,
        required: bool = False,
        column_span: int = 1,
    ) -> FormField:
        field = FormField(label, control, required=required, parent=self)
        self.fields_layout.addWidget(field, row, column, 1, column_span)
        self.fields.append(field)
        self._field_positions.append((row, column, column_span))
        self._reflow_fields(force=True)
        return field

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow_fields()

    def _reflow_fields(self, *, force: bool = False) -> None:
        compact = self.width() < self.COMPACT_BREAKPOINT
        if not force and compact == self._compact_fields:
            return
        for field in self.fields:
            self.fields_layout.removeWidget(field)
        if compact:
            for row, field in enumerate(self.fields):
                self.fields_layout.addWidget(field, row, 0, 1, 2)
        else:
            for field, (row, column, span) in zip(self.fields, self._field_positions, strict=True):
                self.fields_layout.addWidget(field, row, column, 1, span)
        self._compact_fields = compact

    def set_busy(self, busy: bool) -> None:
        controls = [field.control for field in self.fields]
        controls.extend((self.save_button, self.cancel_button))
        if busy:
            self._enabled_before_busy = {control: control.isEnabled() for control in controls}
            for control in controls:
                control.setEnabled(False)
            return
        for control in controls:
            control.setEnabled(self._enabled_before_busy.get(control, True))
        self._enabled_before_busy.clear()

    def show_request_error(self, title: str, message: str) -> None:
        self.feedback.show_message(title, message, severity="error")


class AdminRowActions(QWidget):
    """Neutral edit action plus a chevron-free overflow menu for row actions."""

    def __init__(
        self,
        accessible_name: str,
        parent: QWidget | None = None,
        *,
        on_edit: Callable[[], None] | None = None,
        overflow_actions: Iterable[tuple[str, Callable[[], None]]] = (),
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tableActions")
        self.setProperty("uiSurface", "transparent")
        self.setAccessibleName(accessible_name)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if on_edit is not None:
            self.edit_button = QPushButton("Sửa")
            self.edit_button.setObjectName("actionEditBtn")
            self.edit_button.setAccessibleName(f"Sửa {accessible_name}")
            # QPushButton.clicked emits ``checked: bool``.  Calling the
            # captured zero-argument callback explicitly prevents that value
            # from replacing a row object captured by ``lambda item=item``.
            self.edit_button.clicked.connect(lambda _checked=False, callback=on_edit: callback())
            layout.addWidget(self.edit_button)
        else:
            self.edit_button = None

        specifications = tuple(
            RowAction(
                label,
                callback,
                destructive=("Khóa" in label or "Ngừng" in label or "Xóa" in label),
            )
            for label, callback in overflow_actions
        )
        self.more_button = TableActionMenu(
            specifications,
            self,
            accessible_name=f"Thêm thao tác cho {accessible_name}",
        )
        self.more_button.setVisible(bool(specifications))
        layout.addWidget(self.more_button)


def set_row_actions(table: QWidget, row: int, column: int, widget: QWidget) -> None:
    """Attach an action widget to a model/view row without editable cell data."""

    model = table.model()
    if model is None or not hasattr(table, "setIndexWidget"):
        raise TypeError("table must expose a model and setIndexWidget")
    table.setIndexWidget(model.index(row, column), widget)


def matches_search(item: Mapping[str, Any], query: str, *keys: str) -> bool:
    """Accent-preserving, case-insensitive local filter for loaded Admin lists."""

    needle = query.strip().casefold()
    if not needle:
        return True
    return any(needle in str(item.get(key) or "").casefold() for key in keys)


__all__ = [
    "AdminApiError",
    "AdminFormDialog",
    "AdminApiPage",
    "AdminRowActions",
    "AdminSearchBar",
    "connect_action",
    "matches_search",
    "require_success",
    "set_row_actions",
]
