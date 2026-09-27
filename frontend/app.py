"""Doctor workspace and clinical examination views."""

from __future__ import annotations

from datetime import date

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from frontend.core.config import get_frontend_settings
from frontend.ui.icons import apply_line_icon
from frontend.views.common import format_time_range
from frontend.widgets.app_sidebar import AppSidebar, NavigationItem
from frontend.widgets.application_shell import ApplicationShell
from frontend.widgets.feedback_banner import FeedbackBanner
from frontend.widgets.page_header import PageHeader
from frontend.widgets.state_host import StateHost
from frontend.widgets.status_badge import StatusBadgeDelegate, display_status

API_URL = f"{get_frontend_settings().api_base_url.rstrip('/')}/api/v1/doctor"
STATUS_ROLE = int(Qt.ItemDataRole.UserRole) + 1


def _table_item(
    value: object,
    *,
    alignment: Qt.AlignmentFlag | None = None,
    accessible_label: str | None = None,
) -> QTableWidgetItem:
    """Create a non-editable table item whose complete value stays discoverable."""

    text = "—" if value is None or not str(value).strip() else str(value).strip()
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    item.setToolTip(text)
    item.setData(
        Qt.ItemDataRole.AccessibleTextRole,
        f"{accessible_label}: {text}" if accessible_label else text,
    )
    if alignment is not None:
        item.setTextAlignment(alignment)
    return item


def _display_date(value: object) -> str:
    """Format ISO dates for the Vietnamese locale without hiding unknown values."""

    raw = str(value or "").strip()
    if raw.upper() in {"", "N/A", "NA", "NONE"}:
        return "Chưa cập nhật"
    try:
        return date.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return raw


# ==========================================
# 1. CÁC LUỒNG NỀN (WORKERS - CHỐNG ĐƠ UI)
# ==========================================
class LoginWorker(QThread):
    login_success = Signal(dict)
    login_error = Signal(str)

    def __init__(self, username, password):
        super().__init__()
        self.username = username
        self.password = password

    def run(self):
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.post(
                    f"{API_URL}/login",
                    json={"username": self.username, "password": self.password},
                )
                if res.status_code == 200:
                    self.login_success.emit(res.json())
                else:
                    detail = res.json().get("detail", "Sai tài khoản hoặc mật khẩu!")
                    self.login_error.emit(detail)
        except Exception as e:
            self.login_error.emit(f"Không thể kết nối máy chủ: {str(e)}")


class FetchScheduleWorker(QThread):
    success = Signal(list)
    error = Signal(str)
    unauthorized = Signal(str)

    def __init__(self, doctor_id, token):
        super().__init__()
        self.doctor_id = doctor_id
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.get(
                    f"{API_URL}/schedule?doctor_id={self.doctor_id}", headers=headers
                )
                if res.status_code == 200:
                    self.success.emit(res.json())
                else:
                    try:
                        detail = res.json().get("detail", "Lỗi tải lịch khám")
                    except (TypeError, ValueError):
                        detail = "Lỗi tải lịch khám"
                    if res.status_code == 401:
                        self.unauthorized.emit(str(detail))
                    else:
                        self.error.emit(str(detail))
        except Exception as e:
            self.error.emit(f"Lỗi kết nối: {str(e)}")


class AcceptPatientWorker(QThread):
    success = Signal(dict)
    error = Signal(str)

    def __init__(self, appt_id, doctor_id, token):
        super().__init__()
        self.appt_id = appt_id
        self.doctor_id = doctor_id
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=5.0) as client:
                res = client.put(
                    f"{API_URL}/appointments/{self.appt_id}/accept?doctor_id={self.doctor_id}",
                    headers=headers,
                )
                if res.status_code == 200:
                    self.success.emit(res.json())
                else:
                    self.error.emit(res.json().get("detail", "Lỗi tiếp nhận bệnh nhân"))
        except Exception as e:
            self.error.emit(f"Lỗi kết nối: {str(e)}")


class CompleteExamWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, appt_id, payload, token):
        super().__init__()
        self.appt_id = appt_id
        self.payload = payload
        self.token = token

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            with httpx.Client(timeout=8.0) as client:
                res = client.post(
                    f"{API_URL}/appointments/{self.appt_id}/complete",
                    json=self.payload,
                    headers=headers,
                )
                if res.status_code == 200:
                    self.finished.emit(True, "Hoàn tất ca khám thành công!")
                else:
                    self.finished.emit(
                        False, res.json().get("detail", "Lỗi lưu dữ liệu")
                    )
        except Exception as e:
            self.finished.emit(False, f"Lỗi kết nối máy chủ: {str(e)}")


# ==========================================
# 2. UI: DOCTOR SCHEDULE VIEW
# ==========================================
class DoctorScheduleView(QWidget):
    open_examination = Signal(dict)
    session_expired = Signal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.worker: FetchScheduleWorker | AcceptPatientWorker | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        self.header = PageHeader(
            "Lịch tiếp nhận khám bệnh",
            "Theo dõi và tiếp nhận bệnh nhân trong ngày",
        )
        self.btn_refresh = QPushButton("Làm mới")
        self.btn_refresh.setObjectName("secondaryButton")
        self.btn_refresh.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_refresh.setAccessibleName("Làm mới lịch khám")
        apply_line_icon(
            self.btn_refresh,
            "refresh",
            active_color="#0F766E",
            accessible_name="Làm mới lịch khám",
        )
        self.btn_refresh.clicked.connect(self.load_schedule)
        self.header.add_action(self.btn_refresh)
        layout.addWidget(self.header)

        self.feedback = FeedbackBanner(self)
        layout.addWidget(self.feedback)

        table_card = QFrame()
        table_card.setObjectName("contentCard")
        card_layout = QVBoxLayout(table_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        card_title = QLabel("Hàng đợi khám hôm nay")
        card_title.setObjectName("sectionTitle")
        card_layout.addWidget(card_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Mã hẹn", "Thời gian", "Bệnh nhân", "Lý do khám", "Trạng thái", "Thao tác"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setAccessibleName("Danh sách bệnh nhân chờ khám hôm nay")

        h = self.table.horizontalHeader()
        h.setFixedHeight(40)
        h.setMinimumSectionSize(64)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 76)
        self.table.setColumnWidth(1, 126)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(4, 126)
        self.table.setColumnWidth(5, 148)
        self.table.setItemDelegateForColumn(
            4,
            StatusBadgeDelegate(self.table, status_role=STATUS_ROLE),
        )

        self.state_host = StateHost(self.table, table_card)
        self.state_host.setAccessibleName("Trạng thái lịch khám hôm nay")
        self.state_host.retry_requested.connect(self.load_schedule)
        self.state_host.empty_action_requested.connect(self.load_schedule)
        self.state_host.show_empty(
            "Chưa có bệnh nhân trong hàng đợi hôm nay",
            "Danh sách sẽ tự cập nhật khi lễ tân tiếp nhận bệnh nhân.",
            action_text="Làm mới",
        )

        card_layout.addWidget(self.state_host, 1)
        layout.addWidget(table_card, 1)

    def load_schedule(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.feedback.clear()
        self.state_host.show_loading("Đang tải lịch khám…")
        self.btn_refresh.setEnabled(False)
        self.table.setEnabled(False)
        self.worker = FetchScheduleWorker(
            self.main_window.doctor_id, self.main_window.token
        )
        self.worker.success.connect(self._on_schedule_loaded)
        self.worker.error.connect(self._on_schedule_error)
        self.worker.unauthorized.connect(self._on_schedule_unauthorized)
        self.worker.finished.connect(self._finish_loading)
        self.worker.start()

    def _finish_loading(self) -> None:
        self.btn_refresh.setEnabled(True)
        self.table.setEnabled(True)

    def _on_schedule_loaded(self, items: list[dict]) -> None:
        self.feedback.clear()
        self.render_table(items)

    def _on_schedule_error(self, error: str) -> None:
        self.feedback.clear()
        self.state_host.show_error(
            "Không thể tải lịch khám",
            error,
            retry_text="Thử lại",
        )

    def _on_schedule_unauthorized(self, error: str) -> None:
        """Surface the expired session before returning control to central auth."""

        self.feedback.clear()
        self.state_host.show_error(
            "Phiên đăng nhập đã hết hạn",
            error or "Vui lòng đăng nhập lại để tiếp tục.",
            retry_text="Thử lại",
        )
        self.session_expired.emit()

    def render_table(self, items):
        self.table.clearContents()
        self.table.setRowCount(len(items))

        if not items:
            self.state_host.show_empty(
                "Chưa có bệnh nhân trong hàng đợi hôm nay",
                "Danh sách sẽ tự cập nhật khi lễ tân tiếp nhận bệnh nhân.",
                action_text="Làm mới",
            )
            return

        for row, appt in enumerate(items):
            item_id = _table_item(
                f"#{appt['AppointmentID']}",
                alignment=Qt.AlignmentFlag.AlignCenter,
                accessible_label="Mã hẹn",
            )
            self.table.setItem(row, 0, item_id)

            time_str = format_time_range(appt.get("StartTime"), appt.get("EndTime"))
            item_time = _table_item(
                time_str,
                alignment=Qt.AlignmentFlag.AlignCenter,
                accessible_label="Thời gian khám",
            )
            self.table.setItem(row, 1, item_time)

            pat_name = appt.get("Patient", {}).get("FullName", "—")
            self.table.setItem(
                row,
                2,
                _table_item(pat_name, accessible_label="Bệnh nhân"),
            )

            self.table.setItem(
                row,
                3,
                _table_item(
                    appt.get("Reason") or "Khám bệnh",
                    accessible_label="Lý do khám",
                ),
            )

            status_text = appt.get("Status", "CHECKED_IN")
            item_status = _table_item(
                display_status(status_text, "vi"),
                alignment=Qt.AlignmentFlag.AlignCenter,
                accessible_label="Trạng thái",
            )
            item_status.setData(STATUS_ROLE, status_text)
            self.table.setItem(row, 4, item_status)

            btn_accept = QPushButton(
                "Tiếp tục khám" if status_text == "IN_PROGRESS" else "Tiếp nhận"
            )
            btn_accept.setObjectName("tableActionPrimary")
            btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_accept.setMinimumWidth(116)
            btn_accept.setAccessibleName(f"Tiếp nhận bệnh nhân {pat_name}")
            btn_accept.clicked.connect(
                lambda _checked=False, a=appt, button=btn_accept: self.accept_patient(
                    a, button
                )
            )

            actions_widget = QWidget()
            actions_widget.setObjectName("tableActionContainer")
            actions_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            actions_layout.addWidget(btn_accept)

            self.table.setCellWidget(row, 5, actions_widget)
            self.table.setRowHeight(row, 50)

        self.state_host.show_content()

    def accept_patient(self, appt: dict, button: QPushButton | None = None) -> None:
        if appt.get("Status") == "IN_PROGRESS":
            self.open_examination.emit(appt)
            return

        if self.worker is not None and self.worker.isRunning():
            return

        if button is not None:
            button.setEnabled(False)
            button.setText("Đang tiếp nhận…")
        self.table.setEnabled(False)
        self.worker = AcceptPatientWorker(
            appt["AppointmentID"],
            self.main_window.doctor_id,
            self.main_window.token,
        )
        self.worker.success.connect(lambda _: self._on_patient_accepted(appt))
        self.worker.error.connect(self._on_accept_error)
        self.worker.finished.connect(
            lambda: self._finish_accepting(button, appt.get("Status"))
        )
        self.worker.start()

    def _on_patient_accepted(self, appt: dict) -> None:
        self.feedback.clear()
        self.open_examination.emit(appt)

    def _on_accept_error(self, error: str) -> None:
        self.feedback.show_message(
            "Không thể tiếp nhận bệnh nhân",
            error,
            severity="error",
        )

    def _finish_accepting(
        self,
        button: QPushButton | None,
        status: str | None,
    ) -> None:
        self.table.setEnabled(True)
        if button is not None:
            button.setEnabled(True)
            button.setText("Tiếp tục khám" if status == "IN_PROGRESS" else "Tiếp nhận")


# ==========================================
# 3. UI: MEDICAL EXAMINATION VIEW
# ==========================================
class MedicalExamView(QWidget):
    examination_done = Signal()
    back_to_schedule = Signal()
    STACKED_BREAKPOINT = 1040

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.current_appt = None
        self.worker: CompleteExamWorker | None = None
        self._stacked_layout: bool | None = None
        self._editing_medicine_row: int | None = None
        self._baseline_state: tuple[object, ...] | None = None
        self.setup_ui()

    def setup_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("doctorExamScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setAccessibleName("Nội dung khám bệnh")

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("doctorExamContent")
        self.scroll_content.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )
        content_root = QVBoxLayout(self.scroll_content)
        content_root.setContentsMargins(28, 20, 28, 22)
        content_root.setSpacing(14)

        self.breadcrumb = QPushButton("← Lịch khám hôm nay")
        self.breadcrumb.setObjectName("ghostButton")
        self.breadcrumb.setCursor(Qt.CursorShape.PointingHandCursor)
        self.breadcrumb.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )
        self.breadcrumb.setAccessibleName("Quay lại lịch khám hôm nay")
        self.breadcrumb.clicked.connect(self.back_to_schedule.emit)
        content_root.addWidget(self.breadcrumb, 0, Qt.AlignmentFlag.AlignLeft)

        self.header = PageHeader(
            "Khám bệnh",
            "Ghi nhận chẩn đoán và đơn thuốc cho bệnh nhân",
        )
        self.sub_title = self.header.subtitle_label
        content_root.addWidget(self.header)

        self.feedback = FeedbackBanner(self)
        content_root.addWidget(self.feedback)

        self.patient_summary = QFrame()
        self.patient_summary.setObjectName("contentCard")
        patient_layout = QGridLayout(self.patient_summary)
        patient_layout.setContentsMargins(20, 16, 20, 16)
        patient_layout.setHorizontalSpacing(28)
        patient_layout.setVerticalSpacing(8)

        patient_title = QLabel("Bệnh nhân")
        patient_title.setObjectName("sectionTitle")
        patient_layout.addWidget(patient_title, 0, 0, 1, 3)

        def add_summary_field(column: int, title: str) -> QLabel:
            field = QWidget()
            field_layout = QVBoxLayout(field)
            field_layout.setContentsMargins(0, 0, 0, 0)
            field_layout.setSpacing(2)
            label = QLabel(title)
            label.setObjectName("mutedLabel")
            value = QLabel("—")
            value.setObjectName("fieldValueStrong")
            value.setWordWrap(True)
            value.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            field_layout.addWidget(label)
            field_layout.addWidget(value)
            patient_layout.addWidget(field, 1, column)
            return value

        self.lb_name = add_summary_field(0, "Họ và tên")
        self.lb_gender_dob = add_summary_field(1, "Giới tính và tuổi")
        self.lb_phone = add_summary_field(2, "Số điện thoại")

        address_field = QWidget()
        address_layout = QVBoxLayout(address_field)
        address_layout.setContentsMargins(0, 0, 0, 0)
        address_layout.setSpacing(2)
        address_label = QLabel("Địa chỉ")
        address_label.setObjectName("mutedLabel")
        self.lb_address = QLabel("—")
        self.lb_address.setObjectName("fieldValue")
        self.lb_address.setWordWrap(True)
        self.lb_address.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        address_layout.addWidget(address_label)
        address_layout.addWidget(self.lb_address)
        patient_layout.addWidget(address_field, 2, 0, 1, 3)
        patient_layout.setColumnStretch(0, 4)
        patient_layout.setColumnStretch(1, 3)
        patient_layout.setColumnStretch(2, 3)
        content_root.addWidget(self.patient_summary)

        self.body_layout = QGridLayout()
        self.body_layout.setContentsMargins(0, 0, 0, 0)
        self.body_layout.setHorizontalSpacing(18)
        self.body_layout.setVerticalSpacing(14)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("doctorExamLeftPanel")
        self.left_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        left_col = QVBoxLayout(self.left_panel)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(14)

        card_exam = QFrame()
        card_exam.setObjectName("contentCard")
        exam_card_layout = QVBoxLayout(card_exam)
        exam_card_layout.setContentsMargins(20, 18, 20, 18)
        exam_card_layout.setSpacing(12)

        lbl_exam_title = QLabel("Nội dung khám")
        lbl_exam_title.setObjectName("sectionTitle")
        exam_card_layout.addWidget(lbl_exam_title)

        lbl_sym = QLabel("Triệu chứng *")
        lbl_sym.setObjectName("fieldLabel")
        self.txt_symptoms = QTextEdit()
        self.txt_symptoms.setPlaceholderText("Ghi nhận triệu chứng của bệnh nhân...")
        self._configure_clinical_text_edit(
            self.txt_symptoms,
            "Triệu chứng",
            120,
        )
        exam_card_layout.addWidget(lbl_sym)
        exam_card_layout.addWidget(self.txt_symptoms)

        lbl_diag = QLabel("Chẩn đoán *")
        lbl_diag.setObjectName("fieldLabel")
        self.txt_diagnosis = QTextEdit()
        self.txt_diagnosis.setPlaceholderText("Nhập kết luận chẩn đoán...")
        self._configure_clinical_text_edit(
            self.txt_diagnosis,
            "Chẩn đoán",
            120,
        )
        exam_card_layout.addWidget(lbl_diag)
        exam_card_layout.addWidget(self.txt_diagnosis)

        lbl_note = QLabel("Dặn dò")
        lbl_note.setObjectName("fieldLabel")
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Chế độ ăn uống, sinh hoạt, tái khám...")
        self._configure_clinical_text_edit(
            self.txt_notes,
            "Dặn dò",
            96,
        )
        exam_card_layout.addWidget(lbl_note)
        exam_card_layout.addWidget(self.txt_notes)

        left_col.addWidget(card_exam)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("doctorExamRightPanel")
        self.right_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )
        right_col = QVBoxLayout(self.right_panel)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(14)

        card_pres = QFrame()
        card_pres.setObjectName("contentCard")
        pres_card_layout = QVBoxLayout(card_pres)
        pres_card_layout.setContentsMargins(20, 18, 20, 18)
        pres_card_layout.setSpacing(12)

        lbl_pres_title = QLabel("Đơn thuốc")
        lbl_pres_title.setObjectName("sectionTitle")
        pres_card_layout.addWidget(lbl_pres_title)

        med_form = QGridLayout()
        med_form.setContentsMargins(0, 0, 0, 0)
        med_form.setHorizontalSpacing(10)
        med_form.setVerticalSpacing(6)

        med_label = QLabel("Tên thuốc *")
        med_label.setObjectName("fieldLabel")
        dosage_label = QLabel("Hàm lượng")
        dosage_label.setObjectName("fieldLabel")
        qty_label = QLabel("Số lượng")
        qty_label.setObjectName("fieldLabel")
        instruction_label = QLabel("Hướng dẫn sử dụng *")
        instruction_label.setObjectName("fieldLabel")

        self.in_med = QLineEdit()
        self.in_med.setPlaceholderText("Ví dụ: Paracetamol")
        self.in_med.setAccessibleName("Tên thuốc")
        self.in_dosage = QLineEdit()
        self.in_dosage.setPlaceholderText("Ví dụ: 500 mg")
        self.in_dosage.setAccessibleName("Hàm lượng thuốc")
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 200)
        self.spin_qty.setValue(1)
        self.spin_qty.setAccessibleName("Số lượng thuốc")
        self.in_instructions = QLineEdit()
        self.in_instructions.setPlaceholderText("Ví dụ: Uống 2 lần/ngày sau ăn")
        self.in_instructions.setAccessibleName("Hướng dẫn sử dụng thuốc")
        self.btn_add_medicine = QPushButton("Thêm vào đơn")
        self.btn_add_medicine.setObjectName("primaryButton")
        self.btn_add_medicine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_medicine.setAccessibleName("Thêm thuốc vào đơn")
        self.btn_add_medicine.clicked.connect(self.add_medicine)
        self.btn_cancel_medicine_edit = QPushButton("Hủy sửa")
        self.btn_cancel_medicine_edit.setObjectName("ghostButton")
        self.btn_cancel_medicine_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_medicine_edit.setAccessibleName("Hủy sửa thuốc")
        self.btn_cancel_medicine_edit.clicked.connect(self.cancel_medicine_edit)
        self.btn_cancel_medicine_edit.hide()

        medicine_actions = QWidget()
        medicine_actions_layout = QHBoxLayout(medicine_actions)
        medicine_actions_layout.setContentsMargins(0, 0, 0, 0)
        medicine_actions_layout.setSpacing(6)
        medicine_actions_layout.addWidget(self.btn_cancel_medicine_edit)
        medicine_actions_layout.addWidget(self.btn_add_medicine, 1)

        med_form.addWidget(med_label, 0, 0)
        med_form.addWidget(dosage_label, 0, 1)
        med_form.addWidget(qty_label, 0, 2)
        med_form.addWidget(self.in_med, 1, 0)
        med_form.addWidget(self.in_dosage, 1, 1)
        med_form.addWidget(self.spin_qty, 1, 2)
        med_form.addWidget(instruction_label, 2, 0, 1, 3)
        med_form.addWidget(self.in_instructions, 3, 0, 1, 2)
        med_form.addWidget(medicine_actions, 3, 2)
        med_form.setColumnStretch(0, 3)
        med_form.setColumnStretch(1, 2)
        med_form.setColumnStretch(2, 1)
        pres_card_layout.addLayout(med_form)

        self.prescription_empty = QWidget()
        self.prescription_empty.setObjectName("prescriptionEmptyState")
        empty_layout = QVBoxLayout(self.prescription_empty)
        empty_layout.setContentsMargins(18, 24, 18, 24)
        empty_layout.setSpacing(4)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_title = QLabel("Chưa thêm thuốc")
        empty_title.setObjectName("emptyStateTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        self.prescription_empty.setAccessibleName(
            "Chưa thêm thuốc."
        )

        self.table_med = QTableWidget()
        self.table_med.setColumnCount(5)
        self.table_med.setHorizontalHeaderLabels(
            ["Tên thuốc", "Hàm lượng", "Số lượng", "Hướng dẫn sử dụng", "Thao tác"]
        )
        self.table_med.setAlternatingRowColors(True)
        self.table_med.verticalHeader().setVisible(False)
        self.table_med.setShowGrid(False)
        self.table_med.setWordWrap(True)
        self.table_med.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.table_med.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table_med.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table_med.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table_med.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.table_med.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.table_med.setAccessibleName("Danh sách thuốc trong đơn")
        self.table_med.verticalHeader().setDefaultSectionSize(44)

        h_med = self.table_med.horizontalHeader()
        h_med.setFixedHeight(38)
        h_med.setMinimumSectionSize(72)
        h_med.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        h_med.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h_med.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h_med.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        h_med.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_med.setColumnWidth(0, 140)
        self.table_med.setColumnWidth(1, 104)
        self.table_med.setColumnWidth(2, 78)
        self.table_med.setColumnWidth(4, 76)

        pres_card_layout.addWidget(self.prescription_empty)
        pres_card_layout.addWidget(self.table_med)
        right_col.addWidget(card_pres)

        content_root.addLayout(self.body_layout)
        content_root.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)
        root_layout.addWidget(self.scroll_area, 1)

        self.footer = QFrame(self)
        self.footer.setObjectName("doctorExamFooter")
        footer_layout = QHBoxLayout(self.footer)
        footer_layout.setContentsMargins(28, 10, 28, 14)
        footer_layout.setSpacing(10)
        footer_layout.addStretch(1)
        self.btn_finish = QPushButton("Lưu và hoàn tất khám")
        self.btn_finish.setObjectName("primaryButton")
        self.btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish.setMinimumHeight(44)
        self.btn_finish.setMinimumWidth(240)
        self.btn_finish.setAccessibleName("Lưu và hoàn tất khám")
        self.btn_finish.clicked.connect(self.submit_examination)
        footer_layout.addWidget(self.btn_finish)
        root_layout.addWidget(self.footer)

        self._update_medicine_table_height()
        self._update_body_layout(self.width())

    @staticmethod
    def _configure_clinical_text_edit(
        widget: QTextEdit,
        accessible_name: str,
        preferred_height: int,
    ) -> None:
        widget.setFixedHeight(preferred_height)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        widget.setTabChangesFocus(True)
        widget.setAccessibleName(accessible_name)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._update_body_layout(event.size().width())
        self._resize_medicine_rows()

    def _update_body_layout(self, available_width: int) -> None:
        stacked = available_width < self.STACKED_BREAKPOINT
        if stacked == self._stacked_layout:
            return

        self._stacked_layout = stacked
        self.body_layout.removeWidget(self.left_panel)
        self.body_layout.removeWidget(self.right_panel)
        if stacked:
            self.body_layout.addWidget(
                self.left_panel,
                0,
                0,
                alignment=Qt.AlignmentFlag.AlignTop,
            )
            self.body_layout.addWidget(
                self.right_panel,
                1,
                0,
                alignment=Qt.AlignmentFlag.AlignTop,
            )
            self.body_layout.setColumnStretch(0, 1)
            self.body_layout.setColumnStretch(1, 0)
        else:
            self.body_layout.addWidget(
                self.left_panel,
                0,
                0,
                alignment=Qt.AlignmentFlag.AlignTop,
            )
            self.body_layout.addWidget(
                self.right_panel,
                0,
                1,
                alignment=Qt.AlignmentFlag.AlignTop,
            )
            self.body_layout.setColumnStretch(0, 11)
            self.body_layout.setColumnStretch(1, 9)

        self.scroll_content.setProperty("stacked", stacked)
        self.scroll_content.updateGeometry()

    def _update_medicine_table_height(self) -> None:
        has_medicines = self.table_med.rowCount() > 0
        self.prescription_empty.setVisible(not has_medicines)
        self.table_med.setVisible(has_medicines)
        if not has_medicines:
            return
        header_height = max(38, self.table_med.horizontalHeader().height())
        rows_height = sum(
            self.table_med.rowHeight(row) for row in range(self.table_med.rowCount())
        )
        self.table_med.setFixedHeight(max(132, header_height + rows_height + 4))

    def _resize_medicine_rows(self) -> None:
        """Show up to two instruction lines while retaining the full tooltip."""

        metrics = QFontMetrics(self.table_med.font())
        available_width = max(120, self.table_med.columnWidth(3) - 20)
        two_line_height = metrics.lineSpacing() * 2 + 16
        for row in range(self.table_med.rowCount()):
            item = self.table_med.item(row, 3)
            text = item.text() if item is not None else ""
            bounds = metrics.boundingRect(
                0,
                0,
                available_width,
                1000,
                Qt.TextFlag.TextWordWrap,
                text,
            )
            self.table_med.setRowHeight(
                row,
                max(44, min(two_line_height, bounds.height() + 16)),
            )
        self._update_medicine_table_height()

    @staticmethod
    def _set_field_error(widget: QWidget, has_error: bool) -> None:
        widget.setProperty("hasError", has_error)
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    @staticmethod
    def _patient_age(value: object) -> int | None:
        raw = str(value or "").strip()
        try:
            born = date.fromisoformat(raw[:10])
        except ValueError:
            return None
        today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

    def _prescription_state(self) -> tuple[tuple[str, str, int, str], ...]:
        rows: list[tuple[str, str, int, str]] = []
        for row in range(self.table_med.rowCount()):
            rows.append(
                (
                    self.table_med.item(row, 0).text(),
                    self.table_med.item(row, 1).text(),
                    int(self.table_med.item(row, 2).text()),
                    self.table_med.item(row, 3).text(),
                )
            )
        return tuple(rows)

    def _capture_state(self) -> tuple[object, ...]:
        """Capture editable values so leave-page warnings avoid false negatives."""

        return (
            self.txt_symptoms.toPlainText(),
            self.txt_diagnosis.toPlainText(),
            self.txt_notes.toPlainText(),
            self._prescription_state(),
            self.in_med.text(),
            self.in_dosage.text(),
            self.spin_qty.value(),
            self.in_instructions.text(),
            self._editing_medicine_row,
        )

    def has_unsaved_changes(self) -> bool:
        return (
            self.current_appt is not None
            and self._baseline_state is not None
            and self._capture_state() != self._baseline_state
        )

    def _ask_confirmation(
        self,
        title: str,
        message: str,
        *,
        confirm_text: str,
        cancel_text: str,
    ) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(title)
        dialog.setText(message)
        confirm_button = dialog.addButton(
            confirm_text,
            QMessageBox.ButtonRole.AcceptRole,
        )
        cancel_button = dialog.addButton(
            cancel_text,
            QMessageBox.ButtonRole.RejectRole,
        )
        dialog.setDefaultButton(cancel_button)
        dialog.setEscapeButton(cancel_button)
        dialog.exec()
        return dialog.clickedButton() is confirm_button

    def confirm_discard_changes(self) -> bool:
        if not self.has_unsaved_changes():
            return True
        return self._ask_confirmation(
            "Rời trang khám?",
            "Các thay đổi chưa lưu sẽ bị mất. Bạn có muốn rời trang khám không?",
            confirm_text="Rời trang",
            cancel_text="Ở lại",
        )

    def discard_changes(self) -> None:
        """Restore the loaded appointment while keeping it available to resume."""

        if self.current_appt is not None:
            self.load_patient_data(self.current_appt)

    def load_patient_data(self, appt):
        self.current_appt = appt
        pat = appt.get("Patient", {})
        full_name = pat.get("FullName", "—")
        self.sub_title.setText(
            f"Ghi nhận chẩn đoán và đơn thuốc · Mã hẹn #{appt['AppointmentID']}"
        )
        self.lb_name.setText(full_name)
        self.lb_phone.setText(pat.get("Phone") or "Chưa cập nhật")

        raw_gender = str(pat.get("Gender") or "").strip()
        gender_value = raw_gender.upper()
        gender = {
            "MALE": "Nam",
            "M": "Nam",
            "NAM": "Nam",
            "FEMALE": "Nữ",
            "F": "Nữ",
            "NỮ": "Nữ",
            "OTHER": "Khác",
            "KHÁC": "Khác",
        }.get(
            gender_value,
            "Chưa cập nhật"
            if gender_value in {"", "N/A", "NA", "NONE"}
            else raw_gender,
        )
        dob = _display_date(pat.get("DateOfBirth"))
        age = self._patient_age(pat.get("DateOfBirth"))
        age_text = f"{age} tuổi" if age is not None else "Chưa cập nhật tuổi"
        self.lb_gender_dob.setText(f"{gender} · {age_text}")
        self.lb_gender_dob.setToolTip(f"Ngày sinh: {dob}")
        self.lb_address.setText(pat.get("Address") or "Chưa cập nhật")

        self.feedback.clear()
        self.txt_symptoms.setText(appt.get("Reason") or "")
        self.txt_diagnosis.clear()
        self.txt_notes.clear()
        self._set_field_error(self.txt_symptoms, False)
        self._set_field_error(self.txt_diagnosis, False)
        self.table_med.setRowCount(0)
        self.cancel_medicine_edit()
        self._update_medicine_table_height()
        self.scroll_area.verticalScrollBar().setValue(0)
        self._baseline_state = self._capture_state()

    def add_medicine(self):
        med = self.in_med.text().strip()
        dosage = self.in_dosage.text().strip()
        qty = self.spin_qty.value()
        instructions = self.in_instructions.text().strip()

        self._set_field_error(self.in_med, not med)
        self._set_field_error(self.in_instructions, not instructions)
        if not med or not instructions:
            self.feedback.show_message(
                "Thiếu thông tin thuốc",
                "Vui lòng nhập tên thuốc và hướng dẫn sử dụng.",
                severity="error",
            )
            (self.in_med if not med else self.in_instructions).setFocus()
            return

        self.feedback.clear()
        row = self._editing_medicine_row
        if row is None:
            row = self.table_med.rowCount()
            self.table_med.insertRow(row)
        self.table_med.setItem(
            row,
            0,
            _table_item(med, accessible_label="Tên thuốc"),
        )
        self.table_med.setItem(
            row,
            1,
            _table_item(dosage or "—", accessible_label="Hàm lượng"),
        )
        self.table_med.setItem(
            row,
            2,
            _table_item(
                qty,
                alignment=Qt.AlignmentFlag.AlignCenter,
                accessible_label="Số lượng",
            ),
        )
        self.table_med.setItem(
            row,
            3,
            _table_item(instructions, accessible_label="Hướng dẫn sử dụng"),
        )
        self._set_medicine_action(row)
        self._resize_medicine_rows()
        self.cancel_medicine_edit()

    def _set_medicine_action(self, row: int) -> None:
        button = QToolButton()
        button.setObjectName("tableMoreButton")
        button.setText("⋯")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(
            f"Thao tác với thuốc {self.table_med.item(row, 0).text()}"
        )
        button.setProperty("medicineRow", row)
        button.clicked.connect(
            lambda _checked=False, source=button: self._show_medicine_menu(
                int(source.property("medicineRow")),
                source,
            )
        )

        container = QWidget()
        container.setObjectName("tableActionContainer")
        container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(button)
        self.table_med.setCellWidget(row, 4, container)

    def _show_medicine_menu(self, row: int, source: QToolButton) -> None:
        if not 0 <= row < self.table_med.rowCount():
            return
        menu = QMenu(self)
        edit_action = menu.addAction("Sửa")
        delete_action = menu.addAction("Xóa")
        edit_action.triggered.connect(lambda: self.edit_medicine(row))
        delete_action.triggered.connect(lambda: self._confirm_delete_medicine(row))
        menu.exec(source.mapToGlobal(source.rect().bottomLeft()))

    def _confirm_delete_medicine(self, row: int) -> None:
        if not 0 <= row < self.table_med.rowCount():
            return
        medicine_name = self.table_med.item(row, 0).text()
        if self._ask_confirmation(
            "Xóa thuốc khỏi đơn?",
            f"Bạn có chắc muốn xóa {medicine_name} khỏi đơn thuốc?",
            confirm_text="Xóa thuốc",
            cancel_text="Giữ lại",
        ):
            self.delete_medicine(row)

    def _refresh_medicine_action_rows(self) -> None:
        for row in range(self.table_med.rowCount()):
            container = self.table_med.cellWidget(row, 4)
            if container is None:
                self._set_medicine_action(row)
                continue
            button = container.findChild(QToolButton, "tableMoreButton")
            if button is not None:
                button.setProperty("medicineRow", row)
                button.setAccessibleName(
                    f"Thao tác với thuốc {self.table_med.item(row, 0).text()}"
                )

    def edit_medicine(self, row: int) -> None:
        if not 0 <= row < self.table_med.rowCount():
            return
        self._editing_medicine_row = row
        self.in_med.setText(self.table_med.item(row, 0).text())
        dosage = self.table_med.item(row, 1).text()
        self.in_dosage.setText("" if dosage == "—" else dosage)
        self.spin_qty.setValue(int(self.table_med.item(row, 2).text()))
        self.in_instructions.setText(self.table_med.item(row, 3).text())
        self.btn_add_medicine.setText("Lưu thay đổi")
        self.btn_add_medicine.setAccessibleName("Lưu thay đổi thuốc")
        self.btn_cancel_medicine_edit.show()
        self.in_med.setFocus()
        self.scroll_area.ensureWidgetVisible(self.in_med)

    def cancel_medicine_edit(self) -> None:
        self._editing_medicine_row = None
        self.in_med.clear()
        self.in_dosage.clear()
        self.in_instructions.clear()
        self.spin_qty.setValue(1)
        self._set_field_error(self.in_med, False)
        self._set_field_error(self.in_instructions, False)
        self.btn_add_medicine.setText("Thêm vào đơn")
        self.btn_add_medicine.setAccessibleName("Thêm thuốc vào đơn")
        self.btn_cancel_medicine_edit.hide()

    def delete_medicine(self, row: int) -> None:
        if not 0 <= row < self.table_med.rowCount():
            return
        self.table_med.removeRow(row)
        if self._editing_medicine_row == row:
            self.cancel_medicine_edit()
        elif self._editing_medicine_row is not None and self._editing_medicine_row > row:
            self._editing_medicine_row -= 1
        self._refresh_medicine_action_rows()
        self._resize_medicine_rows()

    def submit_examination(self):
        if self.worker is not None and self.worker.isRunning():
            return

        symptoms = self.txt_symptoms.toPlainText().strip()
        diagnosis = self.txt_diagnosis.toPlainText().strip()

        self._set_field_error(self.txt_symptoms, not symptoms)
        self._set_field_error(self.txt_diagnosis, not diagnosis)
        if not symptoms or not diagnosis:
            self.feedback.show_message(
                "Thiếu thông tin",
                "Vui lòng nhập triệu chứng lâm sàng và chẩn đoán y khoa.",
                severity="error",
            )
            (self.txt_symptoms if not symptoms else self.txt_diagnosis).setFocus()
            self.scroll_area.ensureWidgetVisible(
                self.txt_symptoms if not symptoms else self.txt_diagnosis
            )
            return

        if self.current_appt is None:
            self.feedback.show_message(
                "Chưa chọn bệnh nhân",
                "Quay lại lịch khám và chọn một bệnh nhân trước khi lưu kết quả.",
                severity="error",
            )
            return

        med_items = []
        for r in range(self.table_med.rowCount()):
            med_items.append(
                {
                    "medicine_name": self.table_med.item(r, 0).text(),
                    "dosage": self.table_med.item(r, 1).text(),
                    "quantity": int(self.table_med.item(r, 2).text()),
                    "instructions": self.table_med.item(r, 3).text(),
                }
            )

        payload = {
            "symptoms": symptoms,
            "diagnosis": diagnosis,
            "notes": self.txt_notes.toPlainText().strip() or None,
            "prescription_items": med_items,
        }

        if not self._ask_confirmation(
            "Xác nhận hoàn tất",
            "Lưu kết quả và hoàn tất lượt khám này?",
            confirm_text="Lưu và hoàn tất",
            cancel_text="Kiểm tra lại",
        ):
            return

        self.feedback.clear()
        self.btn_finish.setEnabled(False)
        self.btn_finish.setText("Đang lưu kết quả…")
        self.worker = CompleteExamWorker(
            self.current_appt["AppointmentID"], payload, self.main_window.token
        )
        self.worker.finished.connect(self.on_submit_finished)
        self.worker.start()

    def on_submit_finished(self, ok, msg):
        self.btn_finish.setEnabled(True)
        self.btn_finish.setText("Lưu và hoàn tất khám")
        if ok:
            self._baseline_state = self._capture_state()
            QMessageBox.information(self, "Thành công", msg)
            self.examination_done.emit()
        else:
            self.feedback.show_message(
                "Không thể hoàn tất khám",
                msg,
                severity="error",
            )


class DoctorSidebar(AppSidebar):
    """Role-aware navigation that remains usable in compact mode."""

    schedule_requested = Signal()
    exam_requested = Signal()
    logout_requested = Signal()

    EXPANDED_WIDTH = 264
    COMPACT_WIDTH = 78

    def __init__(self, doctor_name: str, license_number: str, parent=None):
        super().__init__(
            (
                NavigationItem("schedule", "Lịch khám hôm nay", "calendar", "NGHIỆP VỤ"),
                NavigationItem("exam", "Hồ sơ đang khám", "medical"),
            ),
            parent,
            brand_subtitle="Cổng bác sĩ",
            logout_text="Đăng xuất",
        )
        self.setAccessibleName("Điều hướng cổng bác sĩ")
        self._doctor_name = doctor_name
        self._license_number = license_number
        self.schedule_button = self._buttons["schedule"]
        self.exam_button = self._buttons["exam"]
        self.exam_button.setEnabled(False)
        self._user_name_label.setWordWrap(True)
        self._user_role_label.setWordWrap(True)
        self.set_user(
            {"full_name": doctor_name},
            role_label=f"Giấy phép: {license_number}",
        )
        self._user_name_label.setToolTip(doctor_name)
        self._user_role_label.setToolTip(
            f"Số giấy phép hành nghề: {license_number}"
        )
        self.navigation_requested.connect(self._dispatch_navigation)
        self.set_active("schedule")

    def _dispatch_navigation(self, route: str) -> None:
        if route == "schedule":
            self.schedule_requested.emit()
        elif route == "exam":
            self.exam_requested.emit()

    @staticmethod
    def _initials(name: str) -> str:
        words = [word for word in name.strip().split() if word]
        if not words:
            return "BS"
        if len(words) == 1:
            return words[0][0].upper()
        return f"{words[0][0]}{words[-1][0]}".upper()

    def set_active(self, route: str) -> None:
        super().set_active(route)

    def set_exam_patient(self, patient_name: str | None) -> None:
        enabled = bool(patient_name)
        self.exam_button.setEnabled(enabled)
        label = "Hồ sơ đang khám"
        tooltip = f"Hồ sơ đang khám: {patient_name}" if patient_name else label
        self.exam_button.setAccessibleName(tooltip)
        self.exam_button.setToolTip(tooltip)
        self.exam_button.setText("" if self._compact else label)

# ==========================================
# 4. KHUNG CHÍNH: DOCTORDASHBOARD (MAIN CONTAINER)
# ==========================================
class DoctorDashboard(QMainWindow):
    logout_requested = Signal()
    SIDEBAR_COMPACT_BREAKPOINT = 1360

    def __init__(self, session_data):
        super().__init__()
        self._logout_in_progress = False
        self.token = session_data["access_token"]
        self.doctor_id = session_data["doctor_id"]
        self.doctor_name = session_data["doctor_name"]
        license_number = str(session_data.get("license_number") or "").strip()
        self.license_number = (
            "Chưa cập nhật"
            if license_number.upper() in {"", "N/A", "NA", "NONE"}
            else license_number
        )

        self.setWindowTitle(
            f"ClinicCare - Bác sĩ: {self.doctor_name} (Giấy phép: {self.license_number})"
        )
        self.resize(1240, 780)
        self.setMinimumSize(1080, 660)

        self.sidebar = DoctorSidebar(
            self.doctor_name,
            self.license_number,
        )
        self.sidebar.schedule_requested.connect(self.go_to_schedule)
        self.sidebar.exam_requested.connect(self.resume_examination)
        self.sidebar.logout_requested.connect(self.handle_logout)
        # Compatibility alias for callers that referenced the former top-bar button.
        self.btn_schedule_tab = self.sidebar.schedule_button

        self.stack = QStackedWidget()

        self.schedule_view = DoctorScheduleView(self)
        self.exam_view = MedicalExamView(self)

        self.stack.addWidget(self.schedule_view)
        self.stack.addWidget(self.exam_view)

        self.schedule_view.open_examination.connect(self.go_to_exam)
        self.schedule_view.session_expired.connect(self.handle_logout)
        self.exam_view.examination_done.connect(self.finish_examination)
        self.exam_view.back_to_schedule.connect(self.go_to_schedule)

        self.shell = ApplicationShell(self.sidebar, self.stack)
        self.setCentralWidget(self.shell)
        self.shell.set_sidebar_compact(
            self.width() < self.SIDEBAR_COMPACT_BREAKPOINT
        )
        self.schedule_view.load_schedule()

    def go_to_exam(self, appt):
        self.exam_view.load_patient_data(appt)
        self.stack.setCurrentIndex(1)
        patient_name = appt.get("Patient", {}).get("FullName") or "Bệnh nhân"
        self.sidebar.set_exam_patient(patient_name)
        self.sidebar.set_active("exam")

    def resume_examination(self) -> None:
        if self.exam_view.current_appt is None:
            return
        self.stack.setCurrentWidget(self.exam_view)
        self.sidebar.set_active("exam")

    def go_to_schedule(self) -> bool:
        if (
            self.stack.currentWidget() is self.exam_view
            and self.exam_view.has_unsaved_changes()
        ):
            if not self.exam_view.confirm_discard_changes():
                self.sidebar.set_active("exam")
                return False
            self.exam_view.discard_changes()
        self.stack.setCurrentIndex(0)
        self.sidebar.set_active("schedule")
        self.schedule_view.load_schedule()
        return True

    def finish_examination(self) -> None:
        self.exam_view.current_appt = None
        self.exam_view._baseline_state = None
        self.sidebar.set_exam_patient(None)
        self.go_to_schedule()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if hasattr(self, "shell"):
            self.shell.set_sidebar_compact(
                event.size().width() < self.SIDEBAR_COMPACT_BREAKPOINT
            )

    def handle_logout(self):
        if self._logout_in_progress:
            return
        if not self.exam_view.confirm_discard_changes():
            self.sidebar.set_active("exam")
            return
        self._logout_in_progress = True
        self.logout_requested.emit()
        self.close()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._logout_in_progress or self.exam_view.confirm_discard_changes():
            event.accept()
            return
        event.ignore()
