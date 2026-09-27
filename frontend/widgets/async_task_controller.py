"""Reusable non-blocking task lifecycle for dialogs and small widgets."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from PySide6.QtCore import QObject, QThreadPool, Slot
from PySide6.QtWidgets import QWidget

from frontend.api.workers import ApiWorker


class _TaskHandler(QObject):
    """Marshal a worker result back to the controller's GUI thread."""

    def __init__(
        self,
        controller: AsyncTaskController,
        task_key: tuple[str, int],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None],
        on_finished: Callable[[], None] | None,
        controls: tuple[QWidget, ...],
    ) -> None:
        super().__init__(controller)
        self.controller = controller
        self.task_key = task_key
        self.on_success = on_success
        self.on_error = on_error
        self.on_finished = on_finished
        self.controls = controls

    @Slot(object)
    def success(self, result: Any) -> None:
        self.controller._task_succeeded(self, result)

    @Slot(object)
    def error(self, error: Exception) -> None:
        self.controller._task_failed(self, error)

    @Slot()
    def finished(self) -> None:
        self.controller._task_finished(self)


class AsyncTaskController(QObject):
    """Run keyed API work without blocking or updating a stale dialog.

    The owner remains responsible for rendering loading and error messages.
    This controller only owns worker lifetimes, duplicate suppression, control
    disabling, and generation-based invalidation when a dialog is closed.
    """

    def __init__(self, owner: QWidget) -> None:
        super().__init__(owner)
        self._generation = 0
        self._workers: dict[tuple[str, int], ApiWorker] = {}
        self._handlers: dict[tuple[str, int], _TaskHandler] = {}

    def run(
        self,
        key: str,
        operation: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_error: Callable[[Exception], None],
        *,
        controls: Iterable[QWidget] = (),
        on_finished: Callable[[], None] | None = None,
    ) -> bool:
        task_key = (key, self._generation)
        if task_key in self._workers:
            return False

        controlled_widgets = tuple(controls)
        for widget in controlled_widgets:
            widget.setEnabled(False)

        worker = ApiWorker(operation)
        handler = _TaskHandler(
            self,
            task_key,
            on_success,
            on_error,
            on_finished,
            controlled_widgets,
        )
        self._workers[task_key] = worker
        self._handlers[task_key] = handler
        worker.signals.success.connect(handler.success)
        worker.signals.error.connect(handler.error)
        worker.signals.finished.connect(handler.finished)
        QThreadPool.globalInstance().start(worker)
        return True

    def is_running(self, key: str) -> bool:
        return (key, self._generation) in self._workers

    def invalidate(self) -> None:
        """Ignore results that belong to a dialog/session that is no longer active."""

        for handler in tuple(self._handlers.values()):
            if handler.task_key[1] != self._generation:
                continue
            for widget in handler.controls:
                try:
                    widget.setEnabled(True)
                except RuntimeError:
                    pass
        self._generation += 1

    def _is_current(self, handler: _TaskHandler) -> bool:
        return handler.task_key[1] == self._generation

    def _task_succeeded(self, handler: _TaskHandler, result: Any) -> None:
        if self._is_current(handler):
            try:
                handler.on_success(result)
            except (AttributeError, KeyError, TypeError, ValueError) as error:
                handler.on_error(error)

    def _task_failed(self, handler: _TaskHandler, error: Exception) -> None:
        if self._is_current(handler):
            handler.on_error(error)

    def _task_finished(self, handler: _TaskHandler) -> None:
        self._workers.pop(handler.task_key, None)
        self._handlers.pop(handler.task_key, None)
        if self._is_current(handler):
            for widget in handler.controls:
                try:
                    widget.setEnabled(True)
                except RuntimeError:
                    pass
            if handler.on_finished is not None:
                handler.on_finished()
        handler.deleteLater()


__all__ = ["AsyncTaskController"]
