"""Bilingual translation dictionary (Vietnamese and English) for ClinicCare."""

from __future__ import annotations

from typing import Any

TRANSLATIONS: dict[str, dict[str, str]] = {
    # --------------------------------------------------------------------------
    # General & App Branding
    # --------------------------------------------------------------------------
    "app_title": {
        "vi": "ClinicCare - Cổng thông tin Bệnh nhân",
        "en": "ClinicCare - Patient Portal",
    },
    "tagline": {
        "vi": "Thông tin sức khỏe của bạn, hội tụ tại một nơi an tâm.",
        "en": "Your health information, in one calm place.",
    },
    "tagline_desc": {
        "vi": "Xem lại lịch hẹn, hồ sơ bệnh án, đơn thuốc và hóa đơn thông qua một cổng thông tin bệnh nhân an toàn.",
        "en": "Review appointments, medical records, prescriptions, and invoices through one secure patient portal.",
    },
    "hero_bullet_1": {
        "vi": "Quyền truy cập riêng tư vào hồ sơ phòng khám của bạn",
        "en": "Private access to your clinic records",
    },
    "hero_bullet_2": {
        "vi": "Lịch sử cuộc hẹn và thanh toán minh bạch",
        "en": "Clear appointment and billing history",
    },
    "hero_bullet_3": {
        "vi": "Được thiết kế để theo dõi nhanh chóng và đơn giản",
        "en": "Designed for quick, simple follow-up",
    },
    "secure_portal": {
        "vi": "CỔNG BỆNH NHÂN BẢO MẬT",
        "en": "SECURE PATIENT PORTAL",
    },
    "need_help": {
        "vi": "Cần trợ giúp? Liên hệ trực tiếp phòng khám.",
        "en": "Need help? Contact your clinic directly.",
    },
    # --------------------------------------------------------------------------
    # Authentication (Login & Register)
    # --------------------------------------------------------------------------
    "welcome_back": {
        "vi": "CHÀO MỪNG TRỞ LẠI",
        "en": "WELCOME BACK",
    },
    "sign_in_title": {
        "vi": "Đăng nhập vào ClinicCare",
        "en": "Sign in to ClinicCare",
    },
    "sign_in_subtitle": {
        "vi": "Sử dụng tài khoản bệnh nhân của bạn để tiếp tục.",
        "en": "Use your patient username to continue.",
    },
    "username": {
        "vi": "Tên đăng nhập",
        "en": "Username",
    },
    "password": {
        "vi": "Mật khẩu",
        "en": "Password",
    },
    "show_password": {
        "vi": "Hiện mật khẩu",
        "en": "Show password",
    },
    "sign_in_button": {
        "vi": "Đăng nhập",
        "en": "Sign in",
    },
    "create_account_button": {
        "vi": "Đăng ký tài khoản bệnh nhân",
        "en": "Create a patient account",
    },
    "register_title": {
        "vi": "Tạo tài khoản bệnh nhân mới",
        "en": "Create your patient account",
    },
    "register_subtitle": {
        "vi": "Điền các thông tin cơ bản để bắt đầu sử dụng cổng bệnh nhân.",
        "en": "Fill in your details to start using the patient portal.",
    },
    "full_name": {
        "vi": "Họ và tên",
        "en": "Full name",
    },
    "date_of_birth": {
        "vi": "Ngày sinh",
        "en": "Date of birth",
    },
    "gender": {
        "vi": "Giới tính",
        "en": "Gender",
    },
    "gender_male": {
        "vi": "Nam",
        "en": "Male",
    },
    "gender_female": {
        "vi": "Nữ",
        "en": "Female",
    },
    "gender_other": {
        "vi": "Khác",
        "en": "Other",
    },
    "phone": {
        "vi": "Số điện thoại",
        "en": "Phone number",
    },
    "email": {
        "vi": "Email",
        "en": "Email",
    },
    "address": {
        "vi": "Địa chỉ",
        "en": "Address",
    },
    "confirm_password": {
        "vi": "Xác nhận mật khẩu",
        "en": "Confirm password",
    },
    "submit_register": {
        "vi": "Đăng ký tài khoản",
        "en": "Create account",
    },
    "back_to_login": {
        "vi": "Quay lại đăng nhập",
        "en": "Back to login",
    },
    # --------------------------------------------------------------------------
    # Navigation & Sidebar
    # --------------------------------------------------------------------------
    "nav_overview": {
        "vi": "TỔNG QUAN",
        "en": "OVERVIEW",
    },
    "nav_my_care": {
        "vi": "DỊCH VỤ CỦA TÔI",
        "en": "MY CARE",
    },
    "nav_dashboard": {
        "vi": "Bảng điều khiển",
        "en": "Dashboard",
    },
    "nav_booking": {
        "vi": "Đặt lịch khám",
        "en": "Book Appointment",
    },
    "nav_appointments": {
        "vi": "Lịch khám",
        "en": "Appointments",
    },
    "nav_profile": {
        "vi": "Hồ sơ cá nhân",
        "en": "My Profile",
    },
    "nav_medical_history": {
        "vi": "Lịch sử bệnh án",
        "en": "Medical History",
    },
    "nav_invoice_history": {
        "vi": "Lịch sử hóa đơn",
        "en": "Invoice History",
    },
    "nav_logout": {
        "vi": "Đăng xuất",
        "en": "Logout",
    },
    "nav_patient_account": {
        "vi": "Tài khoản bệnh nhân",
        "en": "Patient account",
    },
    "language": {
        "vi": "Ngôn ngữ",
        "en": "Language",
    },
    # --------------------------------------------------------------------------
    # Appointment Booking Wizard
    # --------------------------------------------------------------------------
    "booking_header_title": {
        "vi": "Đặt lịch khám bệnh",
        "en": "Book Appointment",
    },
    "booking_header_subtitle": {
        "vi": "Chọn chuyên khoa, bác sĩ và khung giờ phù hợp để đặt lịch khám",
        "en": "Choose a specialty, doctor, and time slot to book your visit",
    },
    "back_to_appointments": {
        "vi": "Quay lại danh sách",
        "en": "Back to appointments",
    },
    "step_1_indicator": {
        "vi": "BƯỚC 1/4: CHỌN CHUYÊN KHOA",
        "en": "STEP 1/4: SELECT SPECIALTY",
    },
    "step_2_indicator": {
        "vi": "BƯỚC 2/4: CHỌN BÁC SĨ",
        "en": "STEP 2/4: SELECT DOCTOR",
    },
    "step_3_indicator": {
        "vi": "BƯỚC 3/4: CHỌN NGÀY VÀ GIỜ KHÁM",
        "en": "STEP 3/4: SELECT DATE & TIME",
    },
    "step_4_indicator": {
        "vi": "BƯỚC 4/4: XÁC NHẬN VÀ TẠO LỊCH KHÁM",
        "en": "STEP 4/4: CONFIRM & BOOK",
    },
    "step_1_title": {
        "vi": "Bước 1: Chọn chuyên khoa y tế",
        "en": "Step 1: Choose Medical Specialty",
    },
    "step_1_subtitle": {
        "vi": "Tìm kiếm hoặc bấm vào menu sổ xuống để chọn chuyên khoa khám bệnh.",
        "en": "Search or select from the dropdown menu to choose a specialty.",
    },
    "spec_search_placeholder": {
        "vi": "Tìm kiếm hoặc bấm mũi tên sổ xuống để chọn chuyên khoa (Tim mạch, Da liễu...)",
        "en": "Search or click dropdown arrow to select specialty (Cardiology, Dermatology...)",
    },
    "spec_combo_default": {
        "vi": "-- Bấm để chọn chuyên khoa trong danh sách sổ xuống --",
        "en": "-- Click to select specialty from dropdown list --",
    },
    "spec_continue_btn": {
        "vi": "Tiếp tục chọn bác sĩ →",
        "en": "Continue to Doctor Selection →",
    },
    "spec_divider_lbl": {
        "vi": "Hoặc bấm chọn trực tiếp chuyên khoa bên dưới:",
        "en": "Or select directly from the specialties below:",
    },
    "select_this_specialty": {
        "vi": "Chọn chuyên khoa này →",
        "en": "Select this specialty →",
    },
    "affiliated_doctors": {
        "vi": "{count} bác sĩ trực thuộc",
        "en": "{count} affiliated doctors",
    },
    "no_specialty_found": {
        "vi": "Không tìm thấy chuyên khoa",
        "en": "No specialties found",
    },
    "no_specialty_found_desc": {
        "vi": "Thử tìm kiếm với từ khóa khác.",
        "en": "Try searching with different keywords.",
    },
    "step_2_back": {
        "vi": "← Đổi chuyên khoa",
        "en": "← Change specialty",
    },
    "step_2_title": {
        "vi": "Bước 2: Chọn bác sĩ",
        "en": "Step 2: Choose Doctor",
    },
    "experience_years": {
        "vi": "Kinh nghiệm: {years} năm",
        "en": "Experience: {years} years",
    },
    "license_number": {
        "vi": "Số CCHN",
        "en": "License number",
    },
    "clinic": {
        "vi": "Phòng khám",
        "en": "Clinic",
    },
    "select_this_doctor": {
        "vi": "Chọn bác sĩ này →",
        "en": "Select this doctor →",
    },
    "no_doctors_found": {
        "vi": "Không có bác sĩ nào cho chuyên khoa này",
        "en": "No doctors found for this specialty",
    },
    "step_3_back": {
        "vi": "← Chọn lại bác sĩ",
        "en": "← Change doctor",
    },
    "step_3_title": {
        "vi": "Bước 3: Chọn ngày và giờ khám",
        "en": "Step 3: Select Date & Time",
    },
    "select_date_label": {
        "vi": "Chọn ngày khám:",
        "en": "Select appointment date:",
    },
    "future_date_hint": {
        "vi": "*(Chỉ chọn được ngày hôm nay hoặc tương lai)*",
        "en": "*(Only today or future dates can be selected)*",
    },
    "slots_title": {
        "vi": "Các khung giờ khám trong ngày (30 phút/ca):",
        "en": "Available time slots (30 mins/slot):",
    },
    "no_schedule_on_day": {
        "vi": "Bác sĩ không có lịch trực vào ngày này",
        "en": "The doctor has no scheduled shifts on this day",
    },
    "no_schedule_desc": {
        "vi": "Vui lòng chọn ngày khác phù hợp với lịch trực của bác sĩ.",
        "en": "Please choose another date matching the doctor's shift schedule.",
    },
    "step_4_back": {
        "vi": "← Chọn lại giờ khám",
        "en": "← Change time slot",
    },
    "step_4_title": {
        "vi": "Bước 4: Xác nhận thông tin đặt lịch",
        "en": "Step 4: Confirm Booking Details",
    },
    "summary_title": {
        "vi": "Thông tin đặt lịch khám",
        "en": "Appointment Summary",
    },
    "summary_specialty": {
        "vi": "Chuyên khoa",
        "en": "Specialty",
    },
    "summary_doctor": {
        "vi": "Bác sĩ phụ trách",
        "en": "Doctor in charge",
    },
    "summary_location": {
        "vi": "Địa điểm khám",
        "en": "Location",
    },
    "summary_date": {
        "vi": "Ngày khám",
        "en": "Date",
    },
    "summary_time": {
        "vi": "Khung giờ",
        "en": "Time slot",
    },
    "summary_note": {
        "vi": "* Lịch hẹn sau khi gửi sẽ ở trạng thái Chờ xác nhận (PENDING). Bạn có thể đổi hoặc hủy lịch trước giờ khám.",
        "en": "* The appointment will be in PENDING status upon submission. You can reschedule or cancel prior to the visit.",
    },
    "reason_label": {
        "vi": "Lý do khám bệnh / Triệu chứng lâm sàng:",
        "en": "Reason for visit / Clinical symptoms:",
    },
    "reason_placeholder": {
        "vi": "Mô tả cụ thể triệu chứng, tình trạng sức khỏe hoặc yêu cầu khám bệnh...",
        "en": "Describe specific symptoms, health condition, or visit request...",
    },
    "confirm_booking_btn": {
        "vi": "✓ Xác nhận đặt lịch khám",
        "en": "✓ Confirm Appointment Booking",
    },
    "booking_success_title": {
        "vi": "Đặt lịch khám thành công!",
        "en": "Appointment Booked Successfully!",
    },
    "booking_success_msg": {
        "vi": "Lịch khám của bạn đã được ghi nhận vào hệ thống.",
        "en": "Your appointment has been registered into the system.",
    },
    # --------------------------------------------------------------------------
    # Appointment Management & Actions
    # --------------------------------------------------------------------------
    "appointment_detail_title": {
        "vi": "Chi tiết lịch hẹn",
        "en": "Appointment Detail",
    },
    "btn_reschedule": {
        "vi": "Đổi lịch",
        "en": "Reschedule",
    },
    "btn_cancel": {
        "vi": "Hủy lịch",
        "en": "Cancel",
    },
    "btn_new_booking": {
        "vi": "+ Đặt lịch khám mới",
        "en": "+ Book Appointment",
    },
    "cancel_dialog_title": {
        "vi": "Hủy lịch hẹn khám bệnh",
        "en": "Cancel Appointment",
    },
    "cancel_dialog_desc": {
        "vi": "Bạn có chắc chắn muốn hủy lịch hẹn này? Thao tác này không thể hoàn tác.",
        "en": "Are you sure you want to cancel this appointment? This action cannot be undone.",
    },
    "cancel_reason_label": {
        "vi": "Lý do hủy lịch:",
        "en": "Cancellation reason:",
    },
    "cancel_reason_placeholder": {
        "vi": "Nhập lý do hủy (ví dụ: bận việc đột xuất, đổi kế hoạch...)",
        "en": "Enter cancellation reason (e.g., sudden schedule change...)",
    },
    "confirm_cancel_btn": {
        "vi": "Xác nhận hủy lịch",
        "en": "Confirm Cancellation",
    },
    "close_btn": {
        "vi": "Đóng",
        "en": "Close",
    },
    "reschedule_dialog_title": {
        "vi": "Đổi lịch hẹn khám bệnh",
        "en": "Reschedule Appointment",
    },
    "reschedule_new_date": {
        "vi": "Chọn ngày khám mới:",
        "en": "Select new date:",
    },
    "reschedule_new_slot": {
        "vi": "Chọn khung giờ mới:",
        "en": "Select new time slot:",
    },
    "reschedule_reason_label": {
        "vi": "Lý do đổi lịch (tùy chọn):",
        "en": "Reschedule reason (optional):",
    },
    "confirm_reschedule_btn": {
        "vi": "Xác nhận đổi lịch",
        "en": "Confirm Reschedule",
    },
    # --------------------------------------------------------------------------
    # Days of the Week
    # --------------------------------------------------------------------------
    "day_1": {"vi": "Thứ Hai", "en": "Monday"},
    "day_2": {"vi": "Thứ Ba", "en": "Tuesday"},
    "day_3": {"vi": "Thứ Tư", "en": "Wednesday"},
    "day_4": {"vi": "Thứ Năm", "en": "Thursday"},
    "day_5": {"vi": "Thứ Sáu", "en": "Friday"},
    "day_6": {"vi": "Thứ Bảy", "en": "Saturday"},
    "day_7": {"vi": "Chủ Nhật", "en": "Sunday"},
    # --------------------------------------------------------------------------
    # Status Badges
    # --------------------------------------------------------------------------
    "status_pending": {"vi": "Chờ xác nhận", "en": "Pending"},
    "status_confirmed": {"vi": "Đã xác nhận", "en": "Confirmed"},
    "status_checked_in": {"vi": "Đã check-in", "en": "Checked In"},
    "status_in_progress": {"vi": "Đang khám", "en": "In Progress"},
    "status_completed": {"vi": "Đã hoàn thành", "en": "Completed"},
    "status_cancelled": {"vi": "Đã hủy", "en": "Cancelled"},
    # --------------------------------------------------------------------------
    # Date Picker & Calendar
    # --------------------------------------------------------------------------
    "btn_open_calendar": {"vi": "📅 Mở lịch", "en": "📅 Calendar"},
    "quick_select_date": {"vi": "Chọn nhanh ngày:", "en": "Quick date:"},
    "chip_today": {"vi": "Hôm nay", "en": "Today"},
    "chip_tomorrow": {"vi": "Ngày mai", "en": "Tomorrow"},
    "calendar_dialog_title": {"vi": "Chọn ngày khám bệnh", "en": "Select Appointment Date"},
    "calendar_dialog_select": {"vi": "Chọn ngày này", "en": "Select This Date"},
    "calendar_dialog_close": {"vi": "Đóng", "en": "Close"},
    "warn_active_specialty": {
        "vi": "Lưu ý: Bạn đã có lịch hẹn thuộc chuyên khoa này trong ngày đã chọn. Bạn có thể chọn ngày khám khác hoặc hủy lịch cũ.",
        "en": "Notice: You already have an appointment for this specialty on this date. You can choose another date or cancel the existing appointment.",
    },
    "err_pending_specialty": {
        "vi": "Bạn đã có một lịch hẹn trong ngày này thuộc chuyên khoa này. Vui lòng chọn ngày khám khác hoặc hủy lịch hẹn cũ trước khi đặt lịch mới.",
        "en": "You already have an appointment for this specialty on this date. Please choose another date or cancel the existing appointment.",
    },
    "err_same_clinic_same_day": {
        "vi": "Bạn đã có lịch khám tại phòng khám này trong ngày đã chọn.",
        "en": "You already have an appointment at this clinic on this date.",
    },
    # --------------------------------------------------------------------------
    # Booking Modes (By Date vs By Doctor) & Reschedule Doctor
    # --------------------------------------------------------------------------
    "mode_by_date": {"vi": "Chọn theo ngày khám", "en": "Book by Date"},
    "mode_by_doctor": {"vi": "Chọn theo bác sĩ", "en": "Book by Doctor"},
    "lbl_booking_mode": {"vi": "Phương thức đặt lịch:", "en": "Booking method:"},
    "lbl_choose_doctor_on_date": {
        "vi": "Bác sĩ có lịch khám ngày này:",
        "en": "Doctors available on this date:",
    },
    "no_doctor_on_date": {
        "vi": "Không có bác sĩ nào trực vào ngày này. Vui lòng chọn ngày khác.",
        "en": "No doctors available on this date. Please choose another date.",
    },
    "reschedule_choose_doctor": {"vi": "Chọn bác sĩ khám:", "en": "Select doctor:"},
    "lbl_select_time_slot": {"vi": "Chọn khung giờ khám:", "en": "Select time slot:"},
    "lbl_all_doctors_in_spec": {
        "vi": "Danh sách bác sĩ thuộc chuyên khoa:",
        "en": "Doctors in this specialty:",
    },
    "choose_this_doctor_and_slot": {
        "vi": "Chọn bác sĩ & giờ khám →",
        "en": "Select doctor & slot →",
    },
    "doctor_schedule_info": {"vi": "Lịch trực định kỳ:", "en": "Regular schedule:"},
    "step_2_title_by_date": {"vi": "Bước 2: Chọn ngày & Bác sĩ trực", "en": "Step 2: Select Date & Doctor"},
    "step_2_title_by_doctor": {"vi": "Bước 2: Chọn bác sĩ khám", "en": "Step 2: Select Doctor"},
}


def get_translation(key: str, lang: str = "vi", default: str | None = None, **kwargs: Any) -> str:
    """Retrieve translated string by key and language code with variable interpolation."""
    entry = TRANSLATIONS.get(key)
    if not entry:
        return (default if default is not None else key).format(**kwargs)
    text = entry.get(lang) or entry.get("vi") or default or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
