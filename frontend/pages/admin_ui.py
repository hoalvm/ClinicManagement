"""Small UI helpers shared by the legacy Admin management pages.

The Admin screens still use ``QTableWidget`` because their CRUD behaviour is
stable.  These helpers give those tables one predictable, accessible layout
policy without coupling them to the patient portal's model/view stack.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any

from PySide6.QtCore import QObject, Qt, QThreadPool, Signal, Slot
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from frontend.api.workers import ApiWorker
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.loading_indicator import LoadingIndicator
from frontend.widgets.state_host import StateHost


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


def configure_admin_table(
    table: QTableWidget,
    *,
    accessible_name: str,
    stretch_column: int,
    fixed_widths: Mapping[int, int],
) -> None:
    """Apply a bounded, read-only column policy suitable for 1100px windows."""

    table.setAccessibleName(accessible_name)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    header = table.horizontalHeader()
    header.setFixedHeight(38)
    header.setStretchLastSection(False)
    header.setCascadingSectionResizes(False)
    header.setMinimumSectionSize(48)
    for column in range(table.columnCount()):
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header_item = table.horizontalHeaderItem(column)
        if header_item is not None:
            header_item.setToolTip(header_item.text())
            header_item.setData(Qt.ItemDataRole.AccessibleTextRole, header_item.text())

    for column, width in fixed_widths.items():
        table.setColumnWidth(column, width)

    header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)


def table_item(
    value: object,
    *,
    alignment: Qt.AlignmentFlag | None = None,
    tooltip: str | None = None,
    accessible_text: str | None = None,
) -> QTableWidgetItem:
    """Create a non-editable item whose complete value remains discoverable."""

    text = "—" if value is None or str(value).strip() == "" else str(value)
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    if alignment is not None:
        item.setTextAlignment(alignment)
    full_text = tooltip if tooltip is not None else text
    item.setToolTip(full_text)
    item.setData(
        Qt.ItemDataRole.AccessibleTextRole,
        accessible_text if accessible_text is not None else full_text,
    )
    return item


def action_cell(*buttons: QPushButton, accessible_name: str) -> QWidget:
    """Return a transparent, keyboard-accessible action container for a row."""

    container = QWidget()
    container.setObjectName("tableActions")
    container.setProperty("uiSurface", "transparent")
    container.setAccessibleName(accessible_name)
    layout = QHBoxLayout(container)
    layout.setContentsMargins(4, 0, 4, 0)
    layout.setSpacing(6)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    for button in buttons:
        layout.addWidget(button)
    return container


__all__ = [
    "AdminApiError",
    "AdminApiPage",
    "action_cell",
    "configure_admin_table",
    "require_success",
    "table_item",
]
