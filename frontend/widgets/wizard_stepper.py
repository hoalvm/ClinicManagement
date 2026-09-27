"""Compact, accessible progress indicator for multi-step workflows."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


def _refresh_style(widget: QWidget) -> None:
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


class WizardStepper(QFrame):
    """Render one canonical step indicator with stable selected geometry."""

    def __init__(
        self,
        steps: Sequence[str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("wizardStepper")
        self._steps: list[str] = []
        self._current_index = 0
        self._markers: list[QLabel] = []
        self._labels: list[QLabel] = []
        self._connectors: list[QFrame] = []

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(2, 4, 2, 4)
        self._layout.setSpacing(8)
        self.set_steps(steps)

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def steps(self) -> tuple[str, ...]:
        return tuple(self._steps)

    def set_steps(self, steps: Sequence[str]) -> None:
        values = [str(step) for step in steps]
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        self._steps = values
        self._markers.clear()
        self._labels.clear()
        self._connectors.clear()

        for index, text in enumerate(values):
            step = QWidget(self)
            step.setObjectName("wizardStep")
            step_layout = QVBoxLayout(step)
            step_layout.setContentsMargins(0, 0, 0, 0)
            step_layout.setSpacing(4)

            marker = QLabel(str(index + 1), step)
            marker.setObjectName("wizardStepMarker")
            marker.setAlignment(Qt.AlignmentFlag.AlignCenter)
            marker.setFixedSize(26, 26)
            marker.setAccessibleName(text)
            step_layout.addWidget(marker, 0, Qt.AlignmentFlag.AlignHCenter)

            label = QLabel(text, step)
            label.setObjectName("wizardStepLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            label.setWordWrap(True)
            step_layout.addWidget(label)

            self._layout.addWidget(step, 1)
            self._markers.append(marker)
            self._labels.append(label)

            if index < len(values) - 1:
                connector = QFrame(self)
                connector.setObjectName("wizardStepConnector")
                connector.setFixedHeight(2)
                connector.setMinimumWidth(18)
                connector.setMaximumWidth(72)
                connector.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )
                self._layout.addWidget(connector)
                self._connectors.append(connector)

        self.set_current_step(min(self._current_index, max(0, len(values) - 1)))

    def set_current_step(self, index: int) -> None:
        if not self._steps:
            self._current_index = 0
            return
        self._current_index = max(0, min(index, len(self._steps) - 1))
        for item_index, (marker, label) in enumerate(zip(self._markers, self._labels, strict=True)):
            state = (
                "complete"
                if item_index < self._current_index
                else "active" if item_index == self._current_index else "upcoming"
            )
            marker.setProperty("stepState", state)
            label.setProperty("stepState", state)
            marker.setText("✓" if state == "complete" else str(item_index + 1))
            _refresh_style(marker)
            _refresh_style(label)
        for connector_index, connector in enumerate(self._connectors):
            connector.setProperty(
                "stepState",
                "complete" if connector_index < self._current_index else "upcoming",
            )
            _refresh_style(connector)
        self.setAccessibleDescription(
            f"{self._current_index + 1}/{len(self._steps)}: {self._steps[self._current_index]}"
        )
