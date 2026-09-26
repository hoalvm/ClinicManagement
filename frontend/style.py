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
    background-color: #F4F7FB;
    color: #0f172a;
    font-size: 14px;
    selection-background-color: #0f766e;
    selection-color: #ffffff;
}

QMainWindow {
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
QFrame#profileHero,
QFrame#authCard {
    background-color: #ffffff;
    border: 1px solid #D7E0EA;
    border-radius: 14px;
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
QDateEdit,
QTextEdit {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 8px;
    padding: 10px 14px;
    min-height: 28px;
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

QLineEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QTimeEdit:focus,
QDateEdit:focus,
QTextEdit:focus {
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

/* ComboBox dropdown styling */
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 30px;
    border-left: 1px solid #E6EDF3;
    border-top-right-radius: 7px;
    border-bottom-right-radius: 7px;
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
    margin: 0;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #D7E0EA;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #f0fdfa;
    selection-color: #0f766e;
}

QComboBox QAbstractItemView::item {
    min-height: 32px;
    padding: 5px 12px;
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
    padding: 9px 18px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
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
    padding: 3px 10px;
    font-size: 13px;
    font-weight: 600;
    min-height: 26px;
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
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    min-height: 28px;
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
    padding: 4px 12px;
    font-size: 12px;
    font-weight: 600;
    min-height: 28px;
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
    outline: none;
    font-size: 14px;
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
    padding: 11px 14px;
    border: none;
    border-bottom: 2px solid #D7E0EA;
    font-size: 12px;
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
