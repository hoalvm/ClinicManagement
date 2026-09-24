"""Comprehensive, modern, clean stylesheet for ClinicManagement (Admin & Patient Portal).

Prioritizes clean typography, subtle borders, comfortable whitespace,
and minimalist aesthetics without unnecessary icons.
"""

APP_STYLE = """
/* =========================================================================
   1. GLOBAL RESET & BASE STYLES
   ========================================================================= */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
    outline: none;
}

QWidget {
    background-color: #f8fafc;
    color: #0f172a;
    font-size: 13px;
    selection-background-color: #0f766e;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #f8fafc;
}

QDialog {
    background-color: #ffffff;
}

QScrollArea {
    background: transparent;
    border: none;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

/* =========================================================================
   2. TYPOGRAPHY & LABELS
   ========================================================================= */
QLabel {
    background-color: transparent;
    color: #334155;
    font-size: 13px;
}

QLabel#pageTitle {
    color: #0f172a;
    font-size: 24px;
    font-weight: 700;
    padding-bottom: 2px;
}

QLabel#pageSubtitle,
QLabel[uiRole="pageSubtitle"] {
    color: #64748b;
    font-size: 13px;
}

QLabel#sectionTitle {
    color: #0f172a;
    font-size: 16px;
    font-weight: 600;
}

QLabel#sectionEyebrow,
QLabel#filterLabel,
QLabel#sidebarSectionLabel {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#fieldLabel {
    color: #475569;
    font-size: 12px;
    font-weight: 600;
    padding-bottom: 2px;
}

QLabel#fieldValue {
    color: #0f172a;
    font-size: 13px;
    font-weight: 500;
}

QLabel#mutedLabel {
    color: #64748b;
    font-size: 12px;
}

QLabel#errorText {
    color: #dc2626;
    font-size: 12px;
    font-weight: 500;
}

QLabel#successText {
    color: #16a34a;
    font-size: 12px;
    font-weight: 500;
}

/* =========================================================================
   3. CARDS & CONTAINERS (Clean Modern Surfaces)
   ========================================================================= */
QFrame#contentCard,
QFrame#card,
QFrame#tableCard,
QFrame#filterBar,
QFrame#appointmentCard,
QFrame#infoCard,
QFrame#profileHero,
QFrame#authCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
}

QFrame#pageHeader {
    background-color: transparent;
    border: none;
}

/* =========================================================================
   4. FORM INPUTS (Text, Combo, Spin, Date, Time)
   ========================================================================= */
QLineEdit,
QComboBox,
QSpinBox,
QTimeEdit,
QDateEdit,
QTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 22px;
    font-size: 13px;
}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTimeEdit:hover,
QDateEdit:hover,
QTextEdit:hover {
    border-color: #94a3b8;
}

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTimeEdit:focus,
QDateEdit:focus,
QTextEdit:focus {
    border: 2px solid #0f766e;
    background-color: #ffffff;
}

QLineEdit:disabled,
QComboBox:disabled,
QSpinBox:disabled,
QTimeEdit:disabled,
QDateEdit:disabled,
QTextEdit:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* ComboBox dropdown styling */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border-left: 1px solid #e2e8f0;
    border-top-right-radius: 8px;
    border-bottom-right-radius: 8px;
    background-color: #f8fafc;
}

QComboBox::drop-down:hover {
    background-color: #f1f5f9;
}

QComboBox::down-arrow {
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #64748b;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #f0fdfa;
    selection-color: #0f766e;
}

QComboBox QAbstractItemView::item {
    min-height: 28px;
    padding: 4px 10px;
    border-radius: 6px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}

QComboBox QAbstractItemView::item:selected {
    background-color: #f0fdfa;
    color: #0f766e;
    font-weight: 600;
}

/* SpinBox & TimeEdit buttons */
QSpinBox::up-button, QSpinBox::down-button,
QTimeEdit::up-button, QTimeEdit::down-button,
QDateEdit::up-button, QDateEdit::down-button {
    background-color: #f8fafc;
    border-left: 1px solid #e2e8f0;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QTimeEdit::up-button:hover, QTimeEdit::down-button:hover,
QDateEdit::up-button:hover, QDateEdit::down-button:hover {
    background-color: #e2e8f0;
}

/* =========================================================================
   5. BUTTONS (Clean Modern Hierarchy)
   ========================================================================= */
QPushButton {
    background-color: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    min-height: 20px;
}

QPushButton:hover {
    background-color: #115e59;
    border-color: #115e59;
}

QPushButton:pressed {
    background-color: #134e4a;
    border-color: #134e4a;
}

QPushButton:disabled {
    background-color: #e2e8f0;
    color: #94a3b8;
    border-color: #e2e8f0;
}

/* Primary Button variant */
QPushButton#primaryButton {
    background-color: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
}

QPushButton#primaryButton:hover {
    background-color: #115e59;
    border-color: #115e59;
}

QPushButton#primaryButton:pressed {
    background-color: #134e4a;
    border-color: #134e4a;
}

/* Secondary Button variant */
QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
}

QPushButton#secondaryButton:hover {
    background-color: #f8fafc;
    color: #0f766e;
    border-color: #0f766e;
}

QPushButton#secondaryButton:pressed {
    background-color: #f1f5f9;
}

/* Ghost & Icon Button */
QPushButton#ghostButton,
QPushButton#iconButton {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
}

QPushButton#ghostButton:hover,
QPushButton#iconButton:hover {
    background-color: #f1f5f9;
    color: #0f766e;
}

/* Pill buttons inside data tables */
QPushButton#actionEditBtn {
    background-color: #f0fdf4;
    color: #15803d;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    min-height: 22px;
}

QPushButton#actionEditBtn:hover {
    background-color: #dcfce7;
    border-color: #86efac;
}

QPushButton#actionDeleteBtn {
    background-color: #fef2f2;
    color: #b91c1c;
    border: 1px solid #fecaca;
    border-radius: 6px;
    padding: 3px 10px;
    font-size: 12px;
    font-weight: 600;
    min-height: 22px;
}

QPushButton#actionDeleteBtn:hover {
    background-color: #fee2e2;
    border-color: #fca5a5;
}

/* =========================================================================
   6. TABLES (Clean Modern Data Grid)
   ========================================================================= */
QTableWidget,
QTableView {
    background-color: #ffffff;
    color: #1e293b;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    gridline-color: #f1f5f9;
    selection-background-color: #f0fdfa;
    selection-color: #0f766e;
    outline: none;
}

QTableWidget::item,
QTableView::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f1f5f9;
}

QTableWidget::item:selected,
QTableView::item:selected {
    background-color: #f0fdfa;
    color: #0f766e;
    font-weight: 500;
}

QTableWidget::item:hover,
QTableView::item:hover {
    background-color: #f8fafc;
}

QHeaderView {
    background-color: transparent;
    border: none;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 9px 12px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* =========================================================================
   7. ADMIN SIDEBAR (Sleek Dark Modern Navigation)
   ========================================================================= */
QListWidget#adminSidebar {
    background-color: #0f172a;
    border: none;
    padding: 12px 8px;
    outline: none;
}

QListWidget#adminSidebar::item {
    color: #94a3b8;
    padding: 11px 16px;
    border-radius: 8px;
    margin: 3px 0;
    font-size: 13px;
    font-weight: 500;
}

QListWidget#adminSidebar::item:hover {
    background-color: #1e293b;
    color: #f8fafc;
}

QListWidget#adminSidebar::item:selected {
    background-color: #0f766e;
    color: #ffffff;
    font-weight: 600;
}

/* =========================================================================
   8. PATIENT PORTAL SIDEBAR
   ========================================================================= */
QFrame#sidebar {
    background-color: #0f172a;
    border: none;
}

QFrame#sidebar QWidget,
QFrame#sidebar QLabel,
QFrame#sidebar QFrame {
    background-color: transparent;
}

QFrame#sidebar QLabel#sidebarBrandMark {
    background-color: #0f766e;
    color: #ffffff;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 800;
}

QFrame#sidebar QLabel#brandLabel {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}

QFrame#sidebar QLabel#sidebarSubtitle {
    color: #94a3b8;
    font-size: 11px;
}

QFrame#sidebar QLabel#sidebarSectionLabel {
    color: #64748b;
    font-size: 11px;
    font-weight: 700;
}

QFrame#sidebar QFrame#userAvatar {
    background-color: #1e293b;
    border-radius: 8px;
}

QFrame#sidebar QLabel#userAvatarText {
    color: #2dd4bf;
    font-size: 14px;
    font-weight: 700;
}

QFrame#sidebar QLabel#sidebarUserName {
    color: #ffffff;
    font-size: 13px;
    font-weight: 600;
}

QFrame#sidebar QLabel#sidebarUserRole {
    color: #94a3b8;
    font-size: 11px;
}

QFrame#sidebar QComboBox {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 6px 10px;
}

QFrame#sidebar QComboBox::drop-down {
    background-color: transparent;
    border: none;
}

QFrame#sidebar QComboBox QAbstractItemView {
    background-color: #1e293b;
    color: #f1f5f9;
    border: 1px solid #334155;
    selection-background-color: #0f766e;
    selection-color: #ffffff;
}

QPushButton#navButton {
    color: #94a3b8;
    background-color: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 10px 14px;
    min-height: 20px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#navButton:hover {
    color: #f8fafc;
    background-color: #1e293b;
}

QPushButton#navButton:checked {
    color: #ffffff;
    background-color: #0f766e;
    font-weight: 600;
}

QPushButton#logoutButton {
    color: #cbd5e1;
    background-color: transparent;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    text-align: left;
    font-size: 12px;
}

QPushButton#logoutButton:hover {
    color: #f87171;
    border-color: #f87171;
    background-color: #1e293b;
}

/* =========================================================================
   9. STAT CARDS (Dashboard KPIs)
   ========================================================================= */
QFrame#statCard {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    min-height: 80px;
}

QFrame#statCard:hover {
    border-color: #0f766e;
}

QLabel#statValue {
    color: #0f172a;
    font-size: 26px;
    font-weight: 700;
}

QLabel#statTitle {
    color: #64748b;
    font-size: 12px;
    font-weight: 600;
}

/* =========================================================================
   10. STATUS BADGES
   ========================================================================= */
QLabel#statusBadge {
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
}

/* =========================================================================
   11. SCROLLBARS (Minimal, Unobtrusive)
   ========================================================================= */
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px 0 2px 0;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    min-height: 24px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
    height: 0px;
}

QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 2px 0 2px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    min-width: 24px;
    border-radius: 4px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: none;
    width: 0px;
}

/* =========================================================================
   12. TOOLTIPS & DIALOG BUTTONS
   ========================================================================= */
QToolTip {
    background-color: #0f172a;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 5px 9px;
    font-size: 12px;
}

QDialogButtonBox QPushButton {
    min-width: 80px;
}
"""
