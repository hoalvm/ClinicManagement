APP_STYLE = """
QWidget {
    background-color: #f5f6fa;
    font-family: 'Segoe UI';
    font-size: 13px;
    color: #2f3542;
}

QMainWindow {
    background-color: #f5f6fa;
}

/* ---------- Sidebar menu ---------- */
QListWidget {
    background-color: #1e2a3a;
    border: none;
    padding-top: 10px;
    outline: none;
}
QListWidget::item {
    color: #dfe6e9;
    padding: 14px 20px;
    border: none;
}
QListWidget::item:selected {
    background-color: #2563eb;
    color: white;
    border-left: 4px solid #60a5fa;
}
QListWidget::item:hover:!selected {
    background-color: #2c3e50;
}

/* ---------- Labels ---------- */
QLabel {
    font-size: 13px;
    background-color: transparent;
}

/* ---------- Input fields ---------- */
QLineEdit, QComboBox, QSpinBox, QTimeEdit {
    background-color: white;
    border: 1px solid #dcdde1;
    border-radius: 6px;
    padding: 6px 10px;
}
QLineEdit {
    min-height: 32px;
}
QComboBox {
    min-height: 32px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QSpinBox, QTimeEdit {
    min-height: 32px;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTimeEdit:focus {
    border: 1px solid #2563eb;
}

/* ---------- Buttons ---------- */
QTableWidget QPushButton {
    background-color: #fee2e2;
    color: #dc2626;
    border-radius: 6px;
    padding: 4px 8px;
    font-weight: 500;
    font-size: 12px;
    max-width: 56px;
    max-height: 26px;
    outline: none;
}
QTableWidget QPushButton:hover {
    background-color: #fecaca;
}
QTableWidget QPushButton:pressed {
    background-color: #fca5a5;
}
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}

QTableWidget QPushButton {
    background-color: #fee2e2;
    color: #dc2626;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: 500;
    min-height: 28px;
}
}
QTableWidget QPushButton:hover {
    background-color: #fecaca;
}

/* ---------- Table ---------- */
QTableWidget {
    background-color: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    gridline-color: #f1f2f6;
    selection-background-color: #dbeafe;
    selection-color: #1e293b;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #475569;
    padding: 6px;
    border: none;
    border-bottom: 2px solid #e5e7eb;
    font-weight: 600;
}
QTableWidget::item {
    padding: 6px;
}

/* ---------- Scrollbar ---------- */
QScrollBar:vertical {
    background: #f1f2f6;
    width: 10px;
}
QScrollBar::handle:vertical {
    background: #c8ccd4;
    border-radius: 5px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0px;
}
"""