"""Doctor workspace and clinical examination views."""

from __future__ import annotations

from datetime import date

import httpx
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from frontend.core.config import get_frontend_settings
from frontend.ui.icons import apply_line_icon
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
            "Danh sách sẽ tự cập nhật khi lễ tân hoàn tất check-in.",
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
                "Danh sách sẽ tự cập nhật khi lễ tân hoàn tất check-in.",
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

            time_str = f"{appt.get('StartTime', '')} - {appt.get('EndTime', '')}"
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
        content_root.setContentsMargins(28, 20, 28, 28)
        content_root.setSpacing(14)

        self.header = PageHeader(
            "Khám bệnh và chẩn đoán",
            "Bệnh nhân: —",
            show_back=True,
            back_text="Quay lại lịch khám",
        )
        self.header.back_requested.connect(self.back_to_schedule)
        self.sub_title = self.header.subtitle_label
        content_root.addWidget(self.header)

        self.feedback = FeedbackBanner(self)
        content_root.addWidget(self.feedback)

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

        card_pat = QFrame()
        card_pat.setObjectName("contentCard")
        pat_card_layout = QVBoxLayout(card_pat)
        pat_card_layout.setContentsMargins(20, 18, 20, 18)
        pat_card_layout.setSpacing(12)

        lbl_pat_title = QLabel("Thông tin bệnh nhân")
        lbl_pat_title.setObjectName("sectionTitle")
        pat_card_layout.addWidget(lbl_pat_title)

        form_pat = QFormLayout()
        form_pat.setSpacing(8)
        form_pat.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form_pat.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self.lb_name = QLabel("—")
        self.lb_name.setObjectName("fieldValue")
        self.lb_phone = QLabel("—")
        self.lb_gender_dob = QLabel("—")
        self.lb_address = QLabel("—")
        for label in (
            self.lb_name,
            self.lb_phone,
            self.lb_gender_dob,
            self.lb_address,
        ):
            label.setWordWrap(True)
            label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )

        form_pat.addRow("Họ và tên:", self.lb_name)
        form_pat.addRow("Số điện thoại:", self.lb_phone)
        form_pat.addRow("Giới tính / Ngày sinh:", self.lb_gender_dob)
        form_pat.addRow("Địa chỉ:", self.lb_address)
        pat_card_layout.addLayout(form_pat)
        left_col.addWidget(card_pat)

        card_exam = QFrame()
        card_exam.setObjectName("contentCard")
        exam_card_layout = QVBoxLayout(card_exam)
        exam_card_layout.setContentsMargins(20, 18, 20, 18)
        exam_card_layout.setSpacing(12)

        lbl_exam_title = QLabel("Ghi nhận chẩn đoán lâm sàng")
        lbl_exam_title.setObjectName("sectionTitle")
        exam_card_layout.addWidget(lbl_exam_title)

        lbl_sym = QLabel("Triệu chứng lâm sàng (*)")
        lbl_sym.setObjectName("fieldLabel")
        self.txt_symptoms = QTextEdit()
        self.txt_symptoms.setPlaceholderText("Ghi nhận triệu chứng của bệnh nhân...")
        self._configure_clinical_text_edit(
            self.txt_symptoms,
            "Triệu chứng lâm sàng",
        )
        exam_card_layout.addWidget(lbl_sym)
        exam_card_layout.addWidget(self.txt_symptoms)

        lbl_diag = QLabel("Chẩn đoán y khoa (*)")
        lbl_diag.setObjectName("fieldLabel")
        self.txt_diagnosis = QTextEdit()
        self.txt_diagnosis.setPlaceholderText("Nhập kết luận chẩn đoán...")
        self._configure_clinical_text_edit(
            self.txt_diagnosis,
            "Chẩn đoán y khoa",
        )
        exam_card_layout.addWidget(lbl_diag)
        exam_card_layout.addWidget(self.txt_diagnosis)

        lbl_note = QLabel("Ghi chú / Lời dặn của bác sĩ")
        lbl_note.setObjectName("fieldLabel")
        self.txt_notes = QTextEdit()
        self.txt_notes.setPlaceholderText("Chế độ ăn uống, sinh hoạt, tái khám...")
        self._configure_clinical_text_edit(
            self.txt_notes,
            "Ghi chú và lời dặn của bác sĩ",
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

        lbl_pres_title = QLabel("Kê đơn thuốc điện tử")
        lbl_pres_title.setObjectName("sectionTitle")
        pres_card_layout.addWidget(lbl_pres_title)

        med_form = QGridLayout()
        med_form.setContentsMargins(0, 0, 0, 0)
        med_form.setHorizontalSpacing(10)
        med_form.setVerticalSpacing(6)

        med_label = QLabel("Tên thuốc (*)")
        med_label.setObjectName("fieldLabel")
        dosage_label = QLabel("Hàm lượng")
        dosage_label.setObjectName("fieldLabel")
        qty_label = QLabel("Số lượng")
        qty_label.setObjectName("fieldLabel")
        instruction_label = QLabel("Cách dùng (*)")
        instruction_label.setObjectName("fieldLabel")

        self.in_med = QLineEdit()
        self.in_med.setPlaceholderText("Ví dụ: Paracetamol")
        self.in_med.setAccessibleName("Tên thuốc")
        self.in_dosage = QLineEdit()
        self.in_dosage.setPlaceholderText("Ví dụ: 500 mg")
        self.in_dosage.setAccessibleName("Hàm lượng thuốc")
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 200)
        self.spin_qty.setValue(10)
        self.spin_qty.setAccessibleName("Số lượng thuốc")
        self.in_instructions = QLineEdit()
        self.in_instructions.setPlaceholderText("Ví dụ: Uống 2 lần/ngày sau ăn")
        self.in_instructions.setAccessibleName("Cách dùng thuốc")
        self.btn_add_medicine = QPushButton("Thêm thuốc")
        self.btn_add_medicine.setObjectName("primaryButton")
        self.btn_add_medicine.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_medicine.setAccessibleName("Thêm thuốc vào đơn")
        self.btn_add_medicine.clicked.connect(self.add_medicine)

        med_form.addWidget(med_label, 0, 0)
        med_form.addWidget(dosage_label, 0, 1)
        med_form.addWidget(qty_label, 0, 2)
        med_form.addWidget(self.in_med, 1, 0)
        med_form.addWidget(self.in_dosage, 1, 1)
        med_form.addWidget(self.spin_qty, 1, 2)
        med_form.addWidget(instruction_label, 2, 0, 1, 3)
        med_form.addWidget(self.in_instructions, 3, 0, 1, 2)
        med_form.addWidget(self.btn_add_medicine, 3, 2)
        med_form.setColumnStretch(0, 3)
        med_form.setColumnStretch(1, 2)
        med_form.setColumnStretch(2, 1)
        pres_card_layout.addLayout(med_form)

        self.table_med = QTableWidget()
        self.table_med.setColumnCount(4)
        self.table_med.setHorizontalHeaderLabels(
            ["Tên thuốc", "Hàm lượng", "Số lượng", "Hướng dẫn sử dụng"]
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
        h_med.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h_med.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h_med.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h_med.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_med.setColumnWidth(1, 116)
        self.table_med.setColumnWidth(2, 90)

        pres_card_layout.addWidget(self.table_med)
        right_col.addWidget(card_pres)

        self.btn_finish = QPushButton("Hoàn tất khám")
        self.btn_finish.setObjectName("primaryButton")
        self.btn_finish.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_finish.setMinimumHeight(44)
        self.btn_finish.setAccessibleName("Hoàn tất và lưu kết quả khám")
        self.btn_finish.clicked.connect(self.submit_examination)
        right_col.addWidget(self.btn_finish)

        content_root.addLayout(self.body_layout)
        content_root.addStretch(1)
        self.scroll_area.setWidget(self.scroll_content)
        root_layout.addWidget(self.scroll_area)

        self._update_medicine_table_height()
        self._update_body_layout(self.width())

    @staticmethod
    def _configure_clinical_text_edit(widget: QTextEdit, accessible_name: str) -> None:
        widget.setMinimumHeight(92)
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
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
            self.body_layout.setColumnStretch(0, 5)
            self.body_layout.setColumnStretch(1, 6)

        self.scroll_content.setProperty("stacked", stacked)
        self.scroll_content.updateGeometry()

    def _update_medicine_table_height(self) -> None:
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

    def load_patient_data(self, appt):
        self.current_appt = appt
        pat = appt.get("Patient", {})
        full_name = pat.get("FullName", "—")
        self.sub_title.setText(f"Bệnh nhân: {full_name} | Mã hẹn: #{appt['AppointmentID']}")
        self.lb_name.setText(full_name)
        self.lb_phone.setText(pat.get("Phone") or "—")

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
        self.lb_gender_dob.setText(f"{gender} | Ngày sinh: {dob}")
        self.lb_address.setText(pat.get("Address") or "Chưa cập nhật")

        self.feedback.clear()
        self.txt_symptoms.setText(appt.get("Reason") or "")
        self.txt_diagnosis.clear()
        self.txt_notes.clear()
        self._set_field_error(self.txt_symptoms, False)
        self._set_field_error(self.txt_diagnosis, False)
        self.table_med.setRowCount(0)
        self._update_medicine_table_height()
        self.scroll_area.verticalScrollBar().setValue(0)

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
                "Vui lòng nhập tên thuốc và cách dùng.",
                severity="error",
            )
            (self.in_med if not med else self.in_instructions).setFocus()
            return

        self.feedback.clear()
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
            _table_item(instructions, accessible_label="Cách dùng"),
        )
        self._resize_medicine_rows()

        self.in_med.clear()
        self.in_dosage.clear()
        self.in_instructions.clear()
        self.spin_qty.setValue(10)

    def submit_examination(self):
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
        self.btn_finish.setText("Hoàn tất khám")
        if ok:
            QMessageBox.information(self, "Thành công", msg)
            self.examination_done.emit()
        else:
            self.feedback.show_message(
                "Không thể hoàn tất khám",
                msg,
                severity="error",
            )


class DoctorSidebar(QFrame):
    """Role-aware navigation that remains usable in compact mode."""

    schedule_requested = Signal()
    exam_requested = Signal()
    logout_requested = Signal()

    EXPANDED_WIDTH = 232
    COMPACT_WIDTH = 78

    def __init__(self, doctor_name: str, license_number: str, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self.setAccessibleName("Điều hướng cổng bác sĩ")
        self._compact = False
        self._doctor_name = doctor_name
        self._license_number = license_number

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(14, 20, 14, 16)
        self._layout.setSpacing(7)
        self._build_brand()
        self._layout.addSpacing(22)

        self.section_label = QLabel("NGHIỆP VỤ")
        self.section_label.setObjectName("sidebarSectionLabel")
        self._layout.addWidget(self.section_label)

        self.schedule_button = self._navigation_button(
            "Lịch khám hôm nay",
            "calendar",
            self.schedule_requested.emit,
        )
        self.exam_button = self._navigation_button(
            "Hồ sơ đang khám",
            "medical",
            self.exam_requested.emit,
        )
        self.exam_button.setEnabled(False)
        self._layout.addWidget(self.schedule_button)
        self._layout.addWidget(self.exam_button)

        self._layout.addStretch(1)
        self._build_user_context()
        self._layout.addSpacing(10)

        self.logout_button = QPushButton("Đăng xuất")
        self.logout_button.setObjectName("logoutButton")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.setToolTip("Đăng xuất khỏi ClinicCare")
        apply_line_icon(
            self.logout_button,
            "logout",
            active_color="#F87171",
            accessible_name="Đăng xuất",
        )
        self.logout_button.clicked.connect(
            lambda _checked=False: self.logout_requested.emit()
        )
        self._layout.addWidget(self.logout_button)

        self.set_active("schedule")
        self.set_compact(False)

    def _build_brand(self) -> None:
        self.brand_row = QWidget()
        brand_layout = QHBoxLayout(self.brand_row)
        brand_layout.setContentsMargins(4, 0, 2, 0)
        brand_layout.setSpacing(11)

        self.brand_mark = QLabel("C")
        self.brand_mark.setObjectName("sidebarBrandMark")
        self.brand_mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brand_mark.setFixedSize(36, 36)
        self.brand_mark.setAccessibleName("ClinicCare")
        brand_layout.addWidget(self.brand_mark)

        self.brand_text = QWidget()
        brand_text_layout = QVBoxLayout(self.brand_text)
        brand_text_layout.setContentsMargins(0, 1, 0, 0)
        brand_text_layout.setSpacing(0)
        brand_label = QLabel("ClinicCare")
        brand_label.setObjectName("brandLabel")
        brand_subtitle = QLabel("Cổng bác sĩ")
        brand_subtitle.setObjectName("sidebarSubtitle")
        brand_text_layout.addWidget(brand_label)
        brand_text_layout.addWidget(brand_subtitle)
        brand_layout.addWidget(self.brand_text, 1)
        self._layout.addWidget(self.brand_row)

    @staticmethod
    def _initials(name: str) -> str:
        words = [word for word in name.strip().split() if word]
        if not words:
            return "BS"
        if len(words) == 1:
            return words[0][0].upper()
        return f"{words[0][0]}{words[-1][0]}".upper()

    def _build_user_context(self) -> None:
        self.user_row = QFrame()
        self.user_row.setObjectName("sidebarUser")
        user_layout = QHBoxLayout(self.user_row)
        user_layout.setContentsMargins(5, 8, 3, 7)
        user_layout.setSpacing(10)

        avatar = QFrame()
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(38, 38)
        avatar_layout = QVBoxLayout(avatar)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_text = QLabel(self._initials(self._doctor_name))
        avatar_text.setObjectName("userAvatarText")
        avatar_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_layout.addWidget(avatar_text)
        user_layout.addWidget(avatar)

        self.user_text = QWidget()
        user_text_layout = QVBoxLayout(self.user_text)
        user_text_layout.setContentsMargins(0, 0, 0, 0)
        user_text_layout.setSpacing(1)
        name_label = QLabel(self._doctor_name)
        name_label.setObjectName("sidebarUserName")
        name_label.setToolTip(self._doctor_name)
        name_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        role_label = QLabel(f"Bác sĩ • CCHN {self._license_number}")
        role_label.setObjectName("sidebarUserRole")
        role_label.setToolTip(f"Số chứng chỉ hành nghề: {self._license_number}")
        user_text_layout.addWidget(name_label)
        user_text_layout.addWidget(role_label)
        user_layout.addWidget(self.user_text, 1)

        context = f"Bác sĩ {self._doctor_name}, CCHN {self._license_number}"
        self.user_row.setAccessibleName(context)
        self.user_row.setToolTip(context)
        self._layout.addWidget(self.user_row)

    def _navigation_button(self, label: str, icon: str, callback) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setAccessibleName(label)
        button.setToolTip(label)
        button.setProperty("fullLabel", label)
        apply_line_icon(
            button,
            icon,
            active_color="#2DD4BF",
            selected_color="#2DD4BF",
            accessible_name=label,
        )
        button.clicked.connect(lambda _checked=False, handler=callback: handler())
        return button

    def set_active(self, route: str) -> None:
        self.schedule_button.setChecked(route == "schedule")
        self.exam_button.setChecked(route == "exam")

    def set_exam_patient(self, patient_name: str | None) -> None:
        enabled = bool(patient_name)
        self.exam_button.setEnabled(enabled)
        label = "Hồ sơ đang khám"
        tooltip = f"Hồ sơ đang khám: {patient_name}" if patient_name else label
        self.exam_button.setAccessibleName(tooltip)
        self.exam_button.setToolTip(tooltip)
        self.exam_button.setText("" if self._compact else label)

    @property
    def is_compact(self) -> bool:
        return self._compact

    def set_compact(self, compact: bool) -> None:
        compact = bool(compact)
        self._compact = compact
        self.setProperty("compact", compact)
        self.setFixedWidth(self.COMPACT_WIDTH if compact else self.EXPANDED_WIDTH)
        margin = 10 if compact else 14
        self._layout.setContentsMargins(margin, 20, margin, 16)

        self.brand_text.setVisible(not compact)
        self.section_label.setVisible(not compact)
        self.user_text.setVisible(not compact)
        self.schedule_button.setText("" if compact else "Lịch khám hôm nay")
        self.exam_button.setText("" if compact else "Hồ sơ đang khám")
        self.logout_button.setText("" if compact else "Đăng xuất")

        for button in (
            self.schedule_button,
            self.exam_button,
            self.logout_button,
        ):
            button.setProperty("compact", compact)
            button.style().unpolish(button)
            button.style().polish(button)
        self.style().unpolish(self)
        self.style().polish(self)
        self.updateGeometry()


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
            f"ClinicCare - Bác sĩ: {self.doctor_name} (CCHN: {self.license_number})"
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

    def go_to_schedule(self):
        self.stack.setCurrentIndex(0)
        self.sidebar.set_active("schedule")
        self.schedule_view.load_schedule()

    def finish_examination(self) -> None:
        self.exam_view.current_appt = None
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
        self._logout_in_progress = True
        self.logout_requested.emit()
        self.close()
