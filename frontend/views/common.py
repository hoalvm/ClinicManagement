"""Shared view behavior and presentation helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any

from PySide6.QtCore import QObject, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
    QWidget,
)

from frontend.api.api_client import ApiClient, ApiError
from frontend.api.workers import ApiWorker
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.loading_indicator import LoadingIndicator


class _TaskHandler(QObject):
    """Main-thread receiver for one worker's signals."""

    def __init__(
        self,
        view: BaseApiView,
        task_key: tuple[str, int],
        on_success: Callable[[Any], None],
        controls: tuple[QWidget, ...],
        on_finished: Callable[[], None] | None,
        expire_on_401: bool,
    ) -> None:
        super().__init__(view)
        self.view = view
        self.task_key = task_key
        self.generation = task_key[1]
        self.on_success = on_success
        self.controls = controls
        self.on_finished = on_finished
        self.expire_on_401 = expire_on_401

    @Slot(object)
    def success(self, result: Any) -> None:
        self.view._task_succeeded(self, result)

    @Slot(object)
    def error(self, exc: Exception) -> None:
        self.view._task_failed(self, exc)

    @Slot()
    def finished(self) -> None:
        self.view._task_finished(self)


class BaseApiView(QWidget):
    """Base widget that owns worker lifetimes and standard error handling."""

    session_expired = Signal()

    def __init__(self, api_client: ApiClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("pageRoot")
        self.api_client = api_client
        self.loading = LoadingIndicator(parent=self)
        self.feedback = FeedbackBanner(parent=self)
        self._workers: dict[tuple[str, int], ApiWorker] = {}
        self._handlers: dict[tuple[str, int], _TaskHandler] = {}
        self._generation = 0

    def run_api_task(
        self,
        key: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        *,
        controls: Iterable[QWidget] = (),
        loading_text: str = "Loading…",
        on_finished: Callable[[], None] | None = None,
        expire_on_401: bool = True,
    ) -> bool:
        generation = self._generation
        task_key = (key, generation)
        if task_key in self._workers:
            return False

        self.feedback.clear()
        controlled_widgets = tuple(controls)
        for widget in controlled_widgets:
            widget.setEnabled(False)
        self.loading.start(loading_text)

        worker = ApiWorker(operation)
        self._workers[task_key] = worker
        handler = _TaskHandler(
            self,
            task_key,
            on_success,
            controlled_widgets,
            on_finished,
            expire_on_401,
        )
        self._handlers[task_key] = handler
        worker.signals.success.connect(handler.success)
        worker.signals.error.connect(handler.error)
        worker.signals.finished.connect(handler.finished)
        QThreadPool.globalInstance().start(worker)
        return True

    def _task_succeeded(self, handler: _TaskHandler, result: Any) -> None:
        if handler.generation != self._generation:
            return
        try:
            handler.on_success(result)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            import logging
            logging.getLogger(__name__).exception(
                "Task %s on_success callback failed with %s: %s",
                handler.task_key,
                type(exc).__name__,
                exc,
            )
            self.feedback.show_message(
                "Unexpected response",
                "The server response did not contain the expected information.",
                severity="error",
            )

    def _task_failed(self, handler: _TaskHandler, exc: Exception) -> None:
        if handler.generation != self._generation:
            return
        if isinstance(exc, ApiError):
            if exc.status_code == 401 and handler.expire_on_401:
                self.session_expired.emit()
                return
            self.feedback.show_message("Request failed", exc.message, severity="error")
            return
        self.feedback.show_message(
            "Unexpected error",
            "An unexpected error occurred while processing the request.",
            severity="error",
        )

    def _task_finished(self, handler: _TaskHandler) -> None:
        self._workers.pop(handler.task_key, None)
        self._handlers.pop(handler.task_key, None)
        handler.deleteLater()
        if handler.generation != self._generation:
            return
        for widget in handler.controls:
            widget.setEnabled(True)
        if not any(
            worker_generation == handler.generation for _, worker_generation in self._workers
        ):
            self.loading.stop()
        if handler.on_finished:
            handler.on_finished()

    def invalidate_pending(self) -> None:
        """Ignore results from operations started for a previous session."""

        for handler in tuple(self._handlers.values()):
            for widget in handler.controls:
                widget.setEnabled(True)
        self.loading.stop()
        self.feedback.clear()
        self._generation += 1

    def clear_data(self) -> None:
        """Clear patient-specific state. Subclasses override when needed."""


def configure_table(
    table: QTableView,
    headers: list[str],
    *,
    stretch_column: int | None = None,
    column_widths: dict[int, int] | None = None,
) -> QStandardItemModel:
    model = QStandardItemModel(0, len(headers), table)
    model.setHorizontalHeaderLabels(headers)
    table.setModel(model)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSortingEnabled(False)
    table.setShowGrid(False)
    table.setWordWrap(False)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(46)
    header = table.horizontalHeader()
    header.setMinimumSectionSize(72)
    header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    if stretch_column is not None:
        header.setSectionResizeMode(stretch_column, QHeaderView.ResizeMode.Stretch)
    for column, width in (column_widths or {}).items():
        table.setColumnWidth(column, width)
    return model


def table_item(value: object, *, user_data: object | None = None) -> QStandardItem:
    text = display_text(value)
    item = QStandardItem(text)
    # Stretched table columns can elide long diagnoses, reasons, or medication
    # instructions.  A tooltip keeps the complete read-only value accessible.
    item.setToolTip(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
    if user_data is not None:
        item.setData(user_data, Qt.ItemDataRole.UserRole)
    return item


def status_item(value: object) -> QStandardItem:
    status = str(value or "").strip().replace("_", " ").title()
    item = table_item(status)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return item


def display_text(value: object, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def format_date(value: object) -> str:
    if not value:
        return "—"
    try:
        parsed = date.fromisoformat(str(value)[:10])
    except ValueError:
        return str(value)
    return parsed.strftime("%d/%m/%Y")


def format_datetime(value: object) -> str:
    if not value:
        return "—"
    raw = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return str(value)
    return parsed.strftime("%d/%m/%Y %H:%M")


def format_time(value: object) -> str:
    if not value:
        return "—"
    raw = str(value)
    try:
        parsed = time.fromisoformat(raw)
    except ValueError:
        return raw
    return parsed.strftime("%H:%M")


def format_money(value: object) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return "—"
    return f"{amount:,.0f} VND"


def require_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Expected an object response")
    return value


def require_page(value: Any) -> dict[str, Any]:
    page = require_dict(value)
    if not isinstance(page.get("items"), list):
        raise TypeError("Expected paginated items")
    return page
