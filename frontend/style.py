"""Comprehensive, modern, clean stylesheet for ClinicManagement (Admin & Patient Portal).

Prioritizes clean typography, subtle borders, comfortable whitespace,
and minimalist aesthetics without unnecessary icons.
"""

from frontend.ui.design_system import UI_TOKENS

APP_STYLE = """
/* =========================================================================
   1. GLOBAL RESET & BASE STYLES
   ========================================================================= */
* {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
}

QWidget {
    color: #0f172a;
    font-size: 14px;
    selection-background-color: #0f766e;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #F4F7FB;
}

QWidget#pageRoot,
QWidget[uiSurface="page"] {
    background-color: #F4F7FB;
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
    color: #1e293b;
    font-size: 14px;
}

QLabel#pageTitle {
    color: #0f172a;
    font-size: 24px;
    font-weight: 700;
    padding-bottom: 4px;
}

QLabel#pageSubtitle,
QLabel[uiRole="pageSubtitle"] {
    color: #475569;
    font-size: 14px;
}

QLabel#sectionTitle {
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
}

QLabel#sectionEyebrow,
QLabel#filterLabel,
QLabel#sidebarSectionLabel {
    color: #475569;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#fieldLabel {
    color: #1e293b;
    font-size: 14px;
    font-weight: 600;
    padding-bottom: 3px;
}

QLabel#fieldValue {
    color: #0f172a;
    font-size: 14px;
    font-weight: 500;
}

QLabel#mutedLabel {
    color: #475569;
    font-size: 13px;
}

QLabel#errorText {
    color: #dc2626;
    font-size: 13px;
    font-weight: 500;
}

QLabel#successText {
    color: #16a34a;
    font-size: 13px;
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
QFrame#profileHero {
    background-color: #ffffff;
    border: 1px solid #D7E0EA;
    border-radius: 14px;
}

/* Auth Hero & Auth Card (Dual-Panel Layout) */
QFrame#authHero {
    background-color: #ffffff;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
}

QFrame#authCard {
    background-color: #ffffff;
    border: 1px solid #D7E0EA;
    border-radius: 16px;
}

/* Scroll area and container in Auth views */
QScrollArea#authScroll,
QScrollArea#authScroll > QWidget,
QScrollArea#authScroll > QWidget > QWidget,
QWidget#authContainer {
    background-color: transparent;
    border: none;
}

/* Ensure labels, checkboxes, and field wrappers inside auth cards have clean transparent background */
QFrame#authCard QLabel,
QFrame#authCard QCheckBox,
QFrame#authCard QWidget#fieldWrapper {
    background-color: transparent;
}

QFrame#authCard QLineEdit,
QFrame#authCard QComboBox,
QFrame#authCard QDateEdit,
QFrame#authCard QTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    padding: 7px 12px;
    font-size: 13px;
    min-height: 24px;
}

QFrame#authCard QLineEdit[focusVisible="true"],
QFrame#authCard QComboBox[focusVisible="true"],
QFrame#authCard QDateEdit[focusVisible="true"],
QFrame#authCard QTextEdit[focusVisible="true"] {
    border-color: #0f766e;
    background-color: #ffffff;
}

/* Primary and Secondary button variants inside Auth Card */
QFrame#authCard QPushButton#primaryButton {
    background-color: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
    border-radius: 8px;
    font-weight: 600;
}

QFrame#authCard QPushButton#primaryButton:hover {
    background-color: #0D9488;
    border-color: #0D9488;
}

QFrame#authCard QPushButton#primaryButton:pressed {
    background-color: #134e4a;
    border-color: #134e4a;
}

QFrame#authCard QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1.5px solid #CBD5E1;
    border-radius: 8px;
    font-weight: 600;
}

QFrame#authCard QPushButton#secondaryButton:hover {
    background-color: #F8FAFC;
    color: #0f766e;
    border-color: #0f766e;
}

QFrame#authCard QPushButton#secondaryButton:pressed {
    background-color: #f1f5f9;
}

QLabel#authTagLabel {
    color: #0f766e;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
}

QLabel#authMainTitle {
    color: #0f172a;
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

QLabel#loginErrorBanner {
    background-color: #FEF2F2;
    color: #991B1B;
    border: 1px solid #FECACA;
    border-left: 4px solid #DC2626;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#authBrandMark {
    background-color: #0f766e;
    color: #ffffff;
    border-radius: 10px;
    font-size: 20px;
    font-weight: 700;
}

QLabel#authBrand {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.5px;
}

QLabel#authHeroTitle {
    color: #0f172a;
    font-size: 20px;
    font-weight: 700;
    line-height: 1.35;
}

QLabel#authHeroText {
    color: #64748b;
    font-size: 13px;
    line-height: 1.5;
}

QLabel#authHeroBullet {
    color: #334155;
    font-size: 13px;
    font-weight: 500;
    line-height: 1.4;
}

QLabel#authTrustBadge {
    background-color: #F0FDF4;
    color: #166534;
    border: 1px solid #BBF7D0;
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
}

QLabel#authTitle {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
    letter-spacing: -0.3px;
}

QLabel#authSectionHeader {
    color: #0f766e;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding-top: 2px;
    padding-bottom: 0px;
}

/* =========================================================================
   CHECKBOXES
   ========================================================================= */
QCheckBox {
    background-color: transparent;
    color: #475569;
    font-size: 13px;
    font-weight: 500;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1.5px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:hover {
    border-color: #0f766e;
}

QCheckBox::indicator:checked {
    background-color: #0f766e;
    border-color: #0f766e;
}

QFrame#pageHeader {
    background-color: transparent;
    border: none;
}

/* Preview / Summary card (booking) */
QFrame#previewCard {
    background-color: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 12px;
}

/* Cash calc box */
QFrame#cashBox {
    background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
}

/* Receipt card */
QFrame#receiptCard {
    background-color: #F0FDF4;
    border: 2px dashed #16A34A;
    border-radius: 12px;
}

/* =========================================================================
   4. FORM INPUTS (Text, Combo, Spin, Date, Time)
   ========================================================================= */
QLineEdit,
QComboBox,
QSpinBox,
QTimeEdit,
QDateEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 8px;
    padding: 7px 12px;
    min-height: 24px;
    font-size: 14px;
}

QTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
}

QLineEdit:hover,
QComboBox:hover,
QSpinBox:hover,
QTimeEdit:hover,
QDateEdit:hover,
QTextEdit:hover {
    border-color: #94a3b8;
}

QLineEdit[focusVisible="true"],
QComboBox[focusVisible="true"],
QSpinBox[focusVisible="true"],
QTimeEdit[focusVisible="true"],
QDateEdit[focusVisible="true"],
QTextEdit[focusVisible="true"] {
    border: 1.5px solid #0f766e;
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

/* ComboBox dropdown styling. The native Qt arrow is painter-based and DPI safe. */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 34px;
    border-left: 1px solid #E6EDF3;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
    background-color: #f8fafc;
}

QComboBox::drop-down:hover {
    background-color: #f1f5f9;
}

QComboBox[paintedChevron="true"]::drop-down {
    width: 34px;
    border: none;
    background-color: transparent;
}

QComboBox[paintedChevron="true"]::down-arrow {
    image: none;
    width: 0;
    height: 0;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #f0fdfa;
    selection-color: #0f766e;
    outline: 0;
}

QComboBox QAbstractItemView::item {
    min-height: 32px;
    padding: 5px 12px;
    border: 1px solid transparent;
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
    border-left: 1px solid #E6EDF3;
    width: 22px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QTimeEdit::up-button:hover, QTimeEdit::down-button:hover,
QDateEdit::up-button:hover, QDateEdit::down-button:hover {
    background-color: #e2e8f0;
}

/* Radio buttons */
QRadioButton {
    font-size: 14px;
    color: #1e293b;
    spacing: 8px;
}

QRadioButton::indicator {
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid #D7E0EA;
    background-color: white;
}

QRadioButton::indicator:hover {
    border-color: #0f766e;
}

QRadioButton::indicator:checked {
    background-color: #0f766e;
    border-color: #0f766e;
}

/* =========================================================================
   5. BUTTONS (Clean Modern Hierarchy)
   ========================================================================= */
QPushButton {
    background-color: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 14px;
    font-weight: 600;
    min-height: 22px;
    text-align: center;
}

QPushButton:hover {
    background-color: #0D9488;
    border-color: #0D9488;
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
    background-color: #0D9488;
    border-color: #0D9488;
}

QPushButton#primaryButton:pressed {
    background-color: #134e4a;
    border-color: #134e4a;
}

/* Secondary Button variant */
QPushButton#secondaryButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1.5px solid #CBD5E1;
    font-weight: 600;
}

QPushButton#secondaryButton:hover {
    background-color: #F8FAFC;
    color: #0f766e;
    border-color: #0f766e;
}

QPushButton#secondaryButton:pressed {
    background-color: #f1f5f9;
}

/* Danger Button variant (dialog cancels, destructive actions) */
QPushButton#dangerButton {
    background-color: #dc2626;
    color: #ffffff;
    border: 1px solid #dc2626;
}

QPushButton#dangerButton:hover {
    background-color: #b91c1c;
    border-color: #b91c1c;
}

QPushButton#dangerButton:pressed {
    background-color: #991b1b;
    border-color: #991b1b;
}

/* Success Button variant (confirm payment, finalize) */
QPushButton#successButton {
    background-color: #16a34a;
    color: #ffffff;
    border: 1px solid #16a34a;
}

QPushButton#successButton:hover {
    background-color: #15803d;
    border-color: #15803d;
}

QPushButton#successButton:pressed {
    background-color: #166534;
    border-color: #166534;
}

/* Ghost & Icon Button */
QPushButton#ghostButton,
QPushButton#iconButton {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
    min-height: 32px;
}

QPushButton#ghostButton:hover,
QPushButton#iconButton:hover {
    background-color: #f1f5f9;
    color: #0f766e;
}

/* -------------------------------------------------------------------------
   Table action buttons — used in cell widgets (small pill-style)
   ------------------------------------------------------------------------- */
QPushButton#tableActionPrimary,
QPushButton#tableActionInfo,
QPushButton#tableActionSecondary,
QPushButton#tableActionDanger {
    border-radius: 6px;
    padding: 0 10px;
    font-size: 13px;
    font-weight: 600;
    min-height: 30px;
    max-height: 30px;
    text-align: center;
}

QPushButton#tableActionPrimary {
    background-color: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
}

QPushButton#tableActionPrimary:hover {
    background-color: #0D9488;
    border-color: #0D9488;
}

QPushButton#tableActionInfo {
    background-color: #DBEAFE;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}

QPushButton#tableActionInfo:hover {
    background-color: #BFDBFE;
}

QPushButton#tableActionSecondary {
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1px solid #CBD5E1;
}

QPushButton#tableActionSecondary:hover {
    background-color: #e2e8f0;
    color: #0f172a;
}

QPushButton#tableActionDanger {
    background-color: #FEE2E2;
    color: #B91C1C;
    border: 1px solid #FECACA;
}

QPushButton#tableActionDanger:hover {
    background-color: #FECACA;
    border-color: #FCA5A5;
}

/* Legacy pill buttons inside data tables */
QPushButton#actionEditBtn {
    background-color: #f0fdf4;
    color: #15803d;
    border: 1px solid #bbf7d0;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 600;
    min-height: 26px;
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
    padding: 3px 8px;
    font-size: 12px;
    font-weight: 600;
    min-height: 26px;
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
    alternate-background-color: #F8FAFC;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 10px;
    gridline-color: #E6EDF3;
    selection-background-color: #f0fdfa;
    selection-color: #0f766e;
    font-size: 14px;
}

/* The enclosing card already owns the visible surface boundary. */
QFrame#tableCard QTableWidget,
QFrame#tableCard QTableView,
QFrame#contentCard QTableWidget,
QFrame#contentCard QTableView,
QFrame#card QTableWidget,
QFrame#card QTableView {
    border: none;
    border-radius: 8px;
}

QTableWidget::item,
QTableView::item {
    padding: 4px 10px;
    border-bottom: 1px solid #E6EDF3;
}

QTableWidget::item:selected,
QTableView::item:selected {
    background-color: #f0fdfa;
    color: #0f766e;
    font-weight: 600;
}

QTableWidget::item:hover,
QTableView::item:hover {
    background-color: #F4F7FB;
}

QHeaderView {
    background-color: transparent;
    border: none;
}

QHeaderView::section {
    background-color: #F8FAFC;
    color: #475569;
    padding: 8px 12px;
    border: none;
    border-bottom: 2px solid #D7E0EA;
    font-size: 13px;
    font-weight: 700;
}

/* =========================================================================
   7. ADMIN SIDEBAR (Sleek Dark Modern Navigation)
   ========================================================================= */
QListWidget#adminSidebar {
    background-color: #0f172a;
    border: none;
    padding: 12px 8px;
}

QListWidget#adminSidebar::item {
    color: #94a3b8;
    padding: 11px 14px;
    border-radius: 6px;
    border-left: 3px solid transparent;
    margin: 2px 0;
    font-size: 14px;
    font-weight: 500;
}

QListWidget#adminSidebar::item:hover {
    background-color: #1e293b;
    color: #f8fafc;
    border-left: 3px solid #334155;
}

QListWidget#adminSidebar::item:selected {
    background-color: #1e293b;
    color: #ffffff;
    font-weight: 600;
    border-left: 3px solid #0f766e;
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
    border-left: 3px solid transparent;
    border-radius: 6px;
    text-align: left;
    padding: 11px 14px;
    min-height: 20px;
    font-size: 14px;
    font-weight: 500;
}

QPushButton#navButton:hover {
    color: #f8fafc;
    background-color: #1e293b;
    border-left: 3px solid #334155;
}

QPushButton#navButton:checked {
    color: #ffffff;
    background-color: #1e293b;
    border-left: 3px solid #0f766e;
    font-weight: 600;
}

QPushButton#navButton[focusVisible="true"] {
    outline: none;
    border: 1px solid #14b8a6;
    border-left: 3px solid #0f766e;
}

QPushButton#logoutButton {
    color: #cbd5e1;
    background-color: transparent;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 9px 14px;
    text-align: center;
    font-size: 13px;
    min-height: 36px;
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
    border: 1px solid #D7E0EA;
    border-radius: 14px;
    min-height: 90px;
}

QFrame#statCard:hover {
    border-color: #0f766e;
    background-color: #FAFFFE;
}

QLabel#statValue {
    color: #0f172a;
    font-size: 28px;
    font-weight: 700;
}

QLabel#statTitle {
    color: #475569;
    font-size: 13px;
    font-weight: 600;
}

/* =========================================================================
   10. STATUS BADGES
   ========================================================================= */
QLabel#statusBadge {
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
    padding: 3px 10px;
    min-width: 80px;
}

/* =========================================================================
   10b. EMPTY STATE & QUICK ACTIONS BOX
   ========================================================================= */
QFrame#emptyState {
    background-color: #F8FAFC;
    border: 1px dashed #D7E0EA;
    border-radius: 12px;
}

QLabel#emptyStateTitle {
    color: #334155;
    font-size: 15px;
    font-weight: 600;
}

QLabel#emptyStateDescription {
    color: #64748b;
    font-size: 13px;
}

QFrame#quickActionsBox {
    background-color: #ffffff;
    border: 1px solid #D7E0EA;
    border-radius: 12px;
}

QFrame#filterCard {
    background-color: #ffffff;
    border: 1px solid #D7E0EA;
    border-radius: 12px;
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
    background-color: #D7E0EA;
    min-height: 28px;
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
    background-color: #D7E0EA;
    min-width: 28px;
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
    padding: 6px 10px;
    font-size: 13px;
}

QDialogButtonBox QPushButton {
    min-width: 90px;
}

/* =========================================================================
   13. FEEDBACK BANNER (Minimalist Accent Card)
   ========================================================================= */
QFrame#feedbackBanner {
    border-radius: 10px;
    padding: 12px 16px;
}

QFrame#feedbackBanner[severity="info"] {
    background-color: #f0fdfa;
    border: 1px solid #ccfbf1;
    border-left: 4px solid #0f766e;
}

QFrame#feedbackBanner[severity="success"] {
    background-color: #f0fdf4;
    border: 1px solid #dcfce7;
    border-left: 4px solid #16a34a;
}

QFrame#feedbackBanner[severity="error"] {
    background-color: #fef2f2;
    border: 1px solid #fee2e2;
    border-left: 4px solid #dc2626;
}

QLabel#feedbackTitle {
    font-size: 14px;
    font-weight: 700;
}

QFrame#feedbackBanner[severity="info"] QLabel#feedbackTitle {
    color: #0f766e;
}

QFrame#feedbackBanner[severity="success"] QLabel#feedbackTitle {
    color: #166534;
}

QFrame#feedbackBanner[severity="error"] QLabel#feedbackTitle {
    color: #991b1b;
}

QLabel#feedbackText {
    font-size: 13px;
    color: #334155;
}
"""


# Typed-token overrides are intentionally appended so they also normalize
# legacy selectors while screens are migrated incrementally.
APP_STYLE += f"""
/* =========================================================================
   14. DESIGN-SYSTEM FOUNDATION OVERRIDES
   ========================================================================= */
QWidget[uiSurface="transparent"],
QWidget#responsivePageContent,
QWidget#stateHost,
QWidget#stateContent,
QWidget#pagination {{
    background: transparent;
    border: none;
}}

QFrame[uiSurface="card"] {{
    background-color: {UI_TOKENS.surface};
    border: 1px solid {UI_TOKENS.border};
    border-radius: {UI_TOKENS.card_radius}px;
}}

QWidget[uiSurface="dialog"] {{
    background-color: {UI_TOKENS.surface};
}}

QTableView QWidget,
QTableWidget QWidget {{
    background-color: transparent;
}}

QTableView QWidget#tableCellWidget,
QTableWidget QWidget#tableCellWidget,
QWidget[uiRole="tableActionCell"] {{
    background-color: transparent;
    border: none;
}}

QLineEdit[hasError="true"],
QComboBox[hasError="true"],
QSpinBox[hasError="true"],
QTimeEdit[hasError="true"],
QDateEdit[hasError="true"],
QTextEdit[hasError="true"],
QLineEdit[error="true"],
QComboBox[error="true"],
QSpinBox[error="true"],
QTimeEdit[error="true"],
QDateEdit[error="true"],
QTextEdit[error="true"] {{
    border: 2px solid {UI_TOKENS.error};
    background-color: #FFF7F7;
}}

QLineEdit[hasError="true"][focusVisible="true"],
QComboBox[hasError="true"][focusVisible="true"],
QSpinBox[hasError="true"][focusVisible="true"],
QTimeEdit[hasError="true"][focusVisible="true"],
QDateEdit[hasError="true"][focusVisible="true"],
QTextEdit[hasError="true"][focusVisible="true"],
QLineEdit[error="true"][focusVisible="true"],
QComboBox[error="true"][focusVisible="true"],
QSpinBox[error="true"][focusVisible="true"],
QTimeEdit[error="true"][focusVisible="true"],
QDateEdit[error="true"][focusVisible="true"],
QTextEdit[error="true"][focusVisible="true"] {{
    border-color: #B91C1C;
}}

QLineEdit:read-only,
QTextEdit:read-only,
QLineEdit[readOnly="true"],
QTextEdit[readOnly="true"] {{
    background-color: {UI_TOKENS.surface_muted};
    color: {UI_TOKENS.text_muted};
    border-color: {UI_TOKENS.border};
}}

QPushButton[focusVisible="true"] {{
    border: 2px solid {UI_TOKENS.focus};
}}

QLineEdit[focusVisible="true"],
QComboBox[focusVisible="true"],
QSpinBox[focusVisible="true"],
QTimeEdit[focusVisible="true"],
QDateEdit[focusVisible="true"],
QTextEdit[focusVisible="true"] {{
    border: 2px solid {UI_TOKENS.brand};
}}

QTableView[focusVisible="true"],
QTableWidget[focusVisible="true"],
QListWidget[focusVisible="true"] {{
    border: 2px solid {UI_TOKENS.focus};
}}

QPushButton[compact="true"] {{
    min-height: 22px;
    padding: 5px 12px;
}}

QToolButton#tableMoreButton {{
    background-color: {UI_TOKENS.surface};
    color: {UI_TOKENS.text_muted};
    border: 1px solid {UI_TOKENS.border};
    border-radius: 7px;
    min-width: 34px;
    max-width: 34px;
    min-height: 32px;
    max-height: 32px;
    padding: 0;
    font-size: 18px;
    font-weight: 700;
}}

QToolButton#tableMoreButton::menu-indicator {{
    image: none;
    width: 0;
    height: 0;
}}

QToolButton#tableMoreButton:hover {{
    background-color: #F0FDFA;
    color: {UI_TOKENS.brand};
    border-color: #99F6E4;
}}

QToolButton#tableMoreButton:pressed {{
    background-color: #CCFBF1;
    border-color: {UI_TOKENS.brand};
}}

QToolButton#tableMoreButton[focusVisible="true"] {{
    border: 2px solid {UI_TOKENS.focus};
}}

QToolButton#tableMoreButton:disabled {{
    background-color: {UI_TOKENS.disabled_background};
    color: {UI_TOKENS.disabled_text};
    border-color: {UI_TOKENS.border};
}}

/* -------------------------------------------------------------------------
   Table overflow menu (QMenu spawned by TableActionMenu / tableMoreButton)
   Must override Windows palette completely so text is readable in all themes.
   ------------------------------------------------------------------------- */
QMenu#tableActionMenu {{
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 10px;
    padding: 6px 4px;
    font-size: 14px;
    font-weight: 500;
}}

QMenu#tableActionMenu::item {{
    background-color: transparent;
    color: #0f172a;
    padding: 9px 16px;
    min-height: 36px;
    border-radius: 6px;
    margin: 1px 2px;
}}

QMenu#tableActionMenu::item:selected {{
    background-color: #f0fdfa;
    color: #0f766e;
    font-weight: 600;
}}

QMenu#tableActionMenu::item:focus {{
    background-color: #f0fdfa;
    color: #0f766e;
    outline: 2px solid {UI_TOKENS.focus};
    outline-offset: -2px;
}}

QMenu#tableActionMenu::item:disabled {{
    color: #94a3b8;
    background-color: transparent;
}}

QMenu#tableActionMenu::item[destructive="true"] {{
    color: #dc2626;
}}

QMenu#tableActionMenu::item[destructive="true"]:selected {{
    background-color: #fef2f2;
    color: #b91c1c;
}}

QMenu#tableActionMenu::separator {{
    height: 1px;
    background-color: #E6EDF3;
    margin: 4px 8px;
}}

QLabel#fieldValueStrong {{
    color: {UI_TOKENS.text};
    font-weight: 600;
}}

QLabel#amountDue {{
    color: #B91C1C;
    font-size: 18px;
    font-weight: 800;
}}

QLabel#changeAmount {{
    color: {UI_TOKENS.success};
    font-size: 16px;
    font-weight: 700;
}}

QLabel#receiptText {{
    color: #14532D;
    font-family: Consolas, "Courier New", monospace;
    font-size: 13px;
}}

QLabel#paidLabel {{
    color: #166534;
    font-size: 11px;
    font-weight: 600;
}}

QComboBox[paintedChevron="true"]::down-arrow {{
    image: none;
    width: 12px;
    height: 8px;
}}

QFrame#feedbackBanner[severity="warning"] {{
    background-color: #FFFBEB;
    border: 1px solid #FDE68A;
    border-left: 4px solid #D97706;
}}

QFrame#feedbackBanner[severity="warning"] QLabel#feedbackTitle {{
    color: #92400E;
}}

QFrame#emptyState[stateRole="error"] {{
    background-color: #FFF7F7;
    border-color: #FECACA;
}}

QFrame#statCard[focusVisible="true"] {{
    border: 2px solid {UI_TOKENS.focus};
}}

QFrame#sidebar[compact="true"] QPushButton#navButton,
QFrame#sidebar[compact="true"] QPushButton#logoutButton {{
    padding-left: 8px;
    padding-right: 8px;
    text-align: center;
}}
"""


# Booking-flow selectors live here rather than on individual widgets.  The
# object names describe stable component roles; dynamic properties represent
# state and are repolished by the views whenever that state changes.
APP_STYLE += """
/* =========================================================================
   15. PATIENT & RECEPTION BOOKING FLOWS
   ========================================================================= */
QWidget#filterToolbar {
    background-color: #ffffff;
    border: 1px solid #d7e0ea;
    border-radius: 10px;
}

QWidget#filterToolbar QLineEdit,
QWidget#filterToolbar QComboBox,
QWidget#filterToolbar QPushButton {
    min-height: 30px;
}

QLabel#bookingStepIndicator {
    color: #0f766e;
    font-size: 13px;
    font-weight: 700;
}

QFrame#bookingWizardSurface {
    background-color: transparent;
    border: none;
}

QPushButton#bookingContextChip {
    background-color: #ecfdf5;
    color: #0f766e;
    border: 1px solid transparent;
    border-radius: 14px;
    padding: 5px 12px;
    font-size: 12px;
    font-weight: 650;
}

QPushButton#bookingContextChip:hover {
    background-color: #ccfbf1;
}

QPushButton#bookingContextChip[focusVisible="true"] {
    border-color: #14b8a6;
}

QFrame#wizardStepper {
    background-color: transparent;
    border: none;
}

QWidget#wizardStep {
    background-color: transparent;
}

QLabel#wizardStepMarker {
    background-color: #e2e8f0;
    color: #64748b;
    border: 1px solid transparent;
    border-radius: 13px;
    font-size: 12px;
    font-weight: 700;
}

QLabel#wizardStepMarker[stepState="active"] {
    background-color: #0f766e;
    color: #ffffff;
}

QLabel#wizardStepMarker[stepState="complete"] {
    background-color: #ccfbf1;
    color: #0f766e;
}

QLabel#wizardStepLabel {
    color: #64748b;
    font-size: 12px;
    font-weight: 500;
}

QLabel#wizardStepLabel[stepState="active"] {
    color: #0f172a;
    font-weight: 700;
}

QLabel#wizardStepLabel[stepState="complete"] {
    color: #0f766e;
    font-weight: 600;
}

QFrame#wizardStepConnector {
    background-color: #e2e8f0;
    border: none;
}

QFrame#wizardStepConnector[stepState="complete"] {
    background-color: #5eead4;
}

QLabel#bookingSupportingText {
    color: #64748b;
    font-size: 13px;
}

QPushButton#primaryButton[bookingRole="continueAction"] {
    padding: 0 18px;
    font-weight: 600;
}

QLabel#bookingSectionLead {
    color: #475569;
    font-size: 13px;
    font-weight: 600;
    margin-top: 4px;
}

QLabel#bookingSpecialtyName {
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
}

QLabel#bookingAccentMeta {
    color: #0f766e;
    font-size: 12px;
    font-weight: 600;
}

QLabel#bookingModeLabel {
    color: #334155;
    font-size: 13px;
    font-weight: 700;
}

QFrame#bookingSegmentedControl {
    background-color: #f1f5f9;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
}

QPushButton#bookingModeOption {
    background-color: transparent;
    color: #475569;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 6px 14px;
    font-weight: 600;
}

QPushButton#bookingModeOption:hover {
    background-color: #e2e8f0;
}

QPushButton#bookingModeOption[selected="true"] {
    background-color: #0f766e;
    color: #ffffff;
    border-color: transparent;
    font-weight: 700;
}

QPushButton#bookingModeOption[focusVisible="true"] {
    border-color: #14b8a6;
}

QPushButton#bookingDateChip {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
    border-radius: 14px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: 500;
}

QPushButton#bookingDateChip:hover {
    background-color: #e2e8f0;
    border-color: #94a3b8;
}

QPushButton#bookingDateChip[active="true"] {
    background-color: #0f766e;
    color: #ffffff;
    border-color: transparent;
    font-weight: 700;
}

QPushButton#bookingDateChip[focusVisible="true"] {
    border-color: #14b8a6;
}

QLabel#bookingAccentLabel {
    color: #0f766e;
    font-weight: 600;
}

QLabel#bookingDoctorAvatar {
    background-color: #e6f4f2;
    color: #0d5c56;
    border-radius: 20px;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    font-size: 13px;
    font-weight: 700;
}

QLabel#bookingDoctorName {
    color: #0f172a;
    font-size: 15px;
    font-weight: 700;
}

QLabel#bookingDoctorSpecialty {
    color: #0f766e;
    font-size: 13px;
    font-weight: 600;
}

QLabel#bookingCompactText {
    color: #64748b;
    font-size: 12px;
}

QFrame#card[bookingRole="doctorBanner"] {
    background-color: #f8fafc;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 10px;
}

QLabel#bookingScheduleText {
    color: #0f766e;
    font-size: 12px;
    font-weight: 500;
}

QFrame#bookingWarningBanner {
    background-color: #fffbeb;
    border: 1.5px solid #fde68a;
    border-radius: 8px;
    padding: 10px;
}

QLabel#bookingWarningText {
    color: #b45309;
    font-size: 13px;
    font-weight: 600;
}

QLabel#bookingSelectionText {
    color: #334155;
    font-weight: 600;
}

QPushButton#bookingSlotButton {
    background-color: #ffffff;
    color: #0f766e;
    border: 1.5px solid #0f766e;
    border-radius: 8px;
    font-weight: 700;
}

QPushButton#bookingSlotButton:hover {
    background-color: #0f766e;
    color: #ffffff;
}

QPushButton#bookingSlotButton[selected="true"],
QPushButton#bookingSlotButton[selected="true"]:hover {
    background-color: #0f766e;
    color: #ffffff;
    border: 1.5px solid transparent;
}

QPushButton#bookingSlotButton:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
    border: 1px solid #e2e8f0;
}

QPushButton#bookingSlotButton[focusVisible="true"] {
    border-color: #14b8a6;
}

QFrame#card[bookingRole="confirmation"] {
    background-color: #ffffff;
    border: 1.5px solid #cbd5e1;
    border-radius: 10px;
    padding: 18px;
}

QLabel#bookingSummaryDetails {
    color: #1e293b;
    font-size: 14px;
}

QPushButton#primaryButton[bookingRole="submitAction"] {
    min-width: 220px;
    font-size: 15px;
    font-weight: 700;
}

QLabel#patientTypeBadge {
    background-color: #f1f5f9;
    color: #475569;
    border-radius: 10px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#patientTypeBadge[patientState="existing"] {
    background-color: #e0f2fe;
    color: #0369a1;
    font-weight: 700;
}

QPushButton#ghostButton[bookingRole="unselectPatient"] {
    color: #0369a1;
    font-size: 12px;
    font-weight: 600;
    text-decoration: underline;
}

QLabel#bookingInlineFieldLabel {
    color: #475569;
    margin-left: 12px;
    font-weight: 500;
}

QLabel#patientProfileStatusBadge {
    background-color: #f1f5f9;
    color: #64748b;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel#patientProfileStatusBadge[patientState="existing"] {
    background-color: #e0f2fe;
    color: #0284c7;
    font-weight: 700;
}

QLabel#patientProfileStatusBadge[patientState="draft"] {
    background-color: #fef3c7;
    color: #b45309;
    font-weight: 700;
}

QFrame#patientProfileEmptyState {
    background-color: #f8fafc;
    border: 1px dashed #cbd5e1;
    border-radius: 8px;
    padding: 16px;
}

QLabel#patientProfileEmptyTitle {
    color: #475569;
    font-size: 13px;
    font-weight: 700;
}

QLabel#patientProfileEmptyDescription {
    color: #94a3b8;
    font-size: 12px;
}

QLabel#patientProfileMetaLabel {
    color: #64748b;
    font-size: 12px;
}

QLabel#patientProfileName {
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
}

QLabel#patientProfileStrongValue {
    color: #1e293b;
    font-weight: 600;
}

QLabel#patientProfileValue {
    color: #1e293b;
    font-weight: 500;
}

QLabel#patientHistoryEmptyText {
    color: #94a3b8;
    padding: 12px;
    font-size: 12px;
}

QLabel#sectionTitle[bookingRole="previewTitle"] {
    color: #166534;
}

QLabel#bookingPreviewStrongValue {
    color: #14532d;
    font-weight: 600;
}

QLabel#bookingPreviewReason {
    color: #166534;
    font-size: 12px;
}

/* =========================================================================
   16. DIALOGS & SMALL SHARED CONTROLS
   ========================================================================= */
QPushButton#destructiveSecondaryButton {
    background-color: #ffffff;
    color: #b91c1c;
    border: 1px solid #fecaca;
}

QPushButton#destructiveSecondaryButton:hover {
    background-color: #fef2f2;
    border-color: #fca5a5;
}

QFrame#destructiveSummaryCard {
    background-color: #fff7f7;
    border: 1px solid #fecaca;
    border-radius: 8px;
}

QFrame#successSummaryCard {
    background-color: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
}

QLabel#successSummaryText {
    color: #065f46;
    font-size: 13px;
}

QLabel#successSummaryStrongText {
    color: #047857;
    font-size: 13px;
    font-weight: 600;
}

QLabel#calendarDialogTitle {
    color: #0f766e;
    font-size: 15px;
    font-weight: 700;
    margin-bottom: 4px;
}

QLabel#languageLabel,
QLabel#quickActionsLabel {
    color: #475569;
    font-size: 12px;
    font-weight: 700;
}

QComboBox#languageCombo {
    border-radius: 6px;
    padding: 4px 10px;
    min-height: 22px;
    font-size: 12px;
    font-weight: 600;
}

QComboBox#languageCombo::drop-down {
    width: 24px;
}

QComboBox#languageCombo QAbstractItemView::item {
    min-height: 28px;
    padding: 5px 8px;
    font-size: 12px;
    font-weight: 600;
}

QLabel#dashboardSectionTitle {
    color: #0f172a;
    font-size: 16px;
    font-weight: 700;
    margin-top: 8px;
}
"""
