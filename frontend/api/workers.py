"""QRunnable wrapper used to keep network work off the GUI thread."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot


class WorkerSignals(QObject):
    success = Signal(object)
    error = Signal(object)
    finished = Signal()


class ApiWorker(QRunnable):
    """Run a callable in QThreadPool and marshal results through signals."""

    def __init__(self, operation: Callable[[], Any]) -> None:
        super().__init__()
        self.operation = operation
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @Slot()
    def run(self) -> None:
        try:
            result = self.operation()
        except Exception as exc:  # The GUI boundary must normalize all failures.
            self.signals.error.emit(exc)
        else:
            self.signals.success.emit(result)
        finally:
            self.signals.finished.emit()
