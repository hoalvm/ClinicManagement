"""Regression tests for the second-round reusable UI foundations."""

from collections.abc import Iterator

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QLineEdit, QWidget

from frontend.widgets.combo_box import ChevronComboBox
from frontend.widgets.filter_toolbar import FilterToolbar
from frontend.widgets.focus_visible import install_focus_visible


@pytest.fixture(scope="module")
def qt_app() -> Iterator[QApplication]:
    application = QApplication.instance() or QApplication([])
    yield application


def test_filter_toolbar_debounces_search_and_applies_facets_immediately(
    qt_app: QApplication,
) -> None:
    toolbar = FilterToolbar(debounce_ms=20)
    combo = toolbar.add_filter(
        "status",
        [("Tất cả trạng thái", None), ("Đã xác nhận", "CONFIRMED")],
        accessible_name="Trạng thái",
    )
    searches: list[str] = []
    facets: list[tuple[str, object]] = []
    toolbar.search_changed.connect(searches.append)
    toolbar.filter_changed.connect(lambda key, value: facets.append((key, value)))

    toolbar.search_input.setText("  Nguyễn Văn An  ")
    assert searches == []
    assert toolbar.clear_button.isVisible() is False  # Parent has not been shown yet.
    toolbar.flush_search()
    assert searches == ["Nguyễn Văn An"]

    combo.setCurrentIndex(1)
    assert facets == [("status", "CONFIRMED")]
    assert toolbar.values() == {
        "search": "Nguyễn Văn An",
        "status": "CONFIRMED",
    }
    assert toolbar.has_active_filters()
    toolbar.deleteLater()
    qt_app.processEvents()


def test_filter_toolbar_clear_restores_defaults_and_emits_one_coherent_state(
    qt_app: QApplication,
) -> None:
    toolbar = FilterToolbar(debounce_ms=350)
    combo = ChevronComboBox()
    combo.addItem("Tất cả", None)
    combo.addItem("Tiền mặt", "CASH")
    toolbar.add_filter_combo("method", combo, default_index=0)
    states: list[dict[str, object]] = []
    cleared: list[bool] = []
    toolbar.filters_changed.connect(states.append)
    toolbar.clear_requested.connect(lambda: cleared.append(True))

    toolbar.search_input.setText("INV-001")
    combo.setCurrentIndex(1)
    states.clear()
    toolbar.clear()

    assert toolbar.search_input.text() == ""
    assert combo.currentIndex() == 0
    assert not toolbar.has_active_filters()
    assert states == [{"search": "", "method": None}]
    assert cleared == [True]
    toolbar.deleteLater()
    qt_app.processEvents()


def test_filter_toolbar_reflows_without_replacing_controls(qt_app: QApplication) -> None:
    toolbar = FilterToolbar()
    status = toolbar.add_filter("status", ["Tất cả", "Hoạt động"])
    role = toolbar.add_filter("role", ["Tất cả", "Bác sĩ"])

    toolbar.resize(900, 80)
    toolbar._place_controls()
    assert not toolbar.is_compact
    assert toolbar._layout.getItemPosition(toolbar._layout.indexOf(toolbar.search_input))[0] == 0

    toolbar.resize(600, 130)
    toolbar._place_controls()
    assert toolbar.is_compact
    assert not toolbar.is_narrow
    assert toolbar._layout.getItemPosition(toolbar._layout.indexOf(status))[0] == 1

    toolbar.resize(420, 220)
    toolbar._place_controls()
    assert toolbar.is_narrow
    assert toolbar._layout.getItemPosition(toolbar._layout.indexOf(status))[0] == 1
    assert toolbar._layout.getItemPosition(toolbar._layout.indexOf(role))[0] == 2
    toolbar.deleteLater()
    qt_app.processEvents()


def test_focus_visible_marks_keyboard_focus_and_pointer_focus_differently(
    qt_app: QApplication,
) -> None:
    manager = install_focus_visible(qt_app)
    first = QLineEdit()
    second = QLineEdit()

    key_event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Tab,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(first, key_event)
    QApplication.sendEvent(
        first,
        QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.TabFocusReason),
    )
    assert manager.keyboard_mode
    assert first.property("focusVisible") is True

    mouse_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        second.rect().center(),
        second.mapToGlobal(second.rect().center()),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(second, mouse_event)
    QApplication.sendEvent(
        second,
        QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason),
    )
    assert not manager.keyboard_mode
    assert first.property("focusVisible") is False
    assert second.property("focusVisible") is not True

    first.deleteLater()
    second.deleteLater()
    qt_app.processEvents()


def test_focus_visible_marks_managed_composite_not_its_inner_child(
    qt_app: QApplication,
) -> None:
    manager = install_focus_visible(qt_app)
    wrapper = QWidget()
    wrapper.setProperty("managedFocus", True)
    child = QLineEdit(wrapper)

    QApplication.sendEvent(
        child,
        QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.BacktabFocusReason),
    )
    assert manager.visible_owner is wrapper
    assert wrapper.property("focusVisible") is True
    assert child.property("focusVisible") is None

    QApplication.sendEvent(
        child,
        QFocusEvent(QEvent.Type.FocusOut, Qt.FocusReason.OtherFocusReason),
    )
    assert wrapper.property("focusVisible") is False
    wrapper.deleteLater()
    qt_app.processEvents()


def test_focus_visible_cleanup_ignores_deleted_owner(qt_app: QApplication) -> None:
    manager = install_focus_visible(qt_app)
    owner = QLineEdit()
    manager._visible_owner = owner

    owner.deleteLater()
    qt_app.processEvents()
    manager._clear_visible_owner()

    assert manager.visible_owner is None
