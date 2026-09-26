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
    "portal_tag": {
        "vi": "CỔNG THÔNG TIN BỆNH NHÂN",
        "en": "PATIENT PORTAL",
    },
    "welcome_back": {
        "vi": "CỔNG THÔNG TIN BỆNH NHÂN",
        "en": "PATIENT PORTAL",
    },
    "sign_in_title": {
        "vi": "ClinicCare",
        "en": "ClinicCare",
    },
    "sign_in_subtitle": {
        "vi": "Đăng nhập để tiếp tục",
        "en": "Sign in to continue",
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
        "vi": "ClinicCare",
        "en": "ClinicCare",
    },
    "register_subtitle": {
        "vi": "Đăng ký tài khoản bệnh nhân để tiếp tục",
        "en": "Create your patient account to continue",
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
    "register_eyebrow": {
        "vi": "CỔNG THÔNG TIN BỆNH NHÂN",
        "en": "PATIENT PORTAL",
    },
    "account_info": {
        "vi": "Thông tin tài khoản",
        "en": "Account information",
    },
    "personal_info": {
        "vi": "Thông tin cá nhân",
        "en": "Personal information",
    },
    "register_hero_title": {
        "vi": "Khởi đầu hành trình chăm sóc sức khỏe toàn diện.",
        "en": "Begin your journey to comprehensive healthcare.",
    },
    "register_hero_desc": {
        "vi": "Tạo tài khoản bệnh nhân để dễ dàng đặt lịch khám, theo dõi hồ sơ y tế và quản lý hóa đơn viện phí.",
        "en": "Create a patient account to easily book appointments, track medical records, and manage clinic invoices.",
    },
    "register_bullet_1": {
        "vi": "Đặt lịch khám với bác sĩ chuyên khoa nhanh chóng",
        "en": "Fast appointment booking with specialists",
    },
    "register_bullet_2": {
        "vi": "Tra cứu hồ sơ bệnh án và đơn thuốc điện tử an toàn",
        "en": "Secure access to medical records and prescriptions",
    },
    "register_bullet_3": {
        "vi": "Theo dõi chi phí và hóa đơn thanh toán minh bạch",
        "en": "Transparent tracking of clinic fees and invoices",
    },
    "register_bullet_4": {
        "vi": "Bảo mật tuyệt đối thông tin sức khỏe cá nhân",
        "en": "Complete privacy and security for personal health data",
    },
    "username_placeholder": {
        "vi": "Nhập tên đăng nhập...",
        "en": "Enter your username...",
    },
    "password_placeholder": {
        "vi": "Nhập mật khẩu (tối thiểu 8 ký tự)...",
        "en": "Enter password (min 8 characters)...",
    },
    "confirm_password_placeholder": {
        "vi": "Nhập lại mật khẩu...",
        "en": "Re-enter your password...",
    },
    "full_name_placeholder": {
        "vi": "Nhập họ và tên...",
        "en": "Enter your full name...",
    },
    "phone_placeholder": {
        "vi": "Nhập số điện thoại...",
        "en": "Enter your phone number...",
    },
    "email_placeholder": {
        "vi": "Nhập địa chỉ email...",
        "en": "Enter your email address...",
    },
    "address_placeholder": {
        "vi": "Nhập địa chỉ nơi ở...",
        "en": "Enter residential address...",
    },
    "already_have_account": {
        "vi": "Đã có tài khoản? Đăng nhập ngay",
        "en": "Already have an account? Sign in",
    },
    "create_account_help": {
        "vi": "Cần hỗ trợ đăng ký? Liên hệ trực tiếp phòng khám.",
        "en": "Need help registering? Contact your clinic directly.",
    },
    "err_username_required": {
        "vi": "Tên đăng nhập không được để trống.",
        "en": "Username is required.",
    },
    "err_password_len": {
        "vi": "Mật khẩu phải có ít nhất 8 ký tự.",
        "en": "Password must be at least 8 characters.",
    },
    "err_password_match": {
        "vi": "Mật khẩu xác nhận không khớp.",
        "en": "Passwords do not match.",
    },
    "err_fullname_required": {
        "vi": "Họ và tên không được để trống.",
        "en": "Full name is required.",
    },
    "err_email_invalid": {
        "vi": "Địa chỉ email không hợp lệ.",
        "en": "Enter a valid email address.",
    },
    "err_phone_invalid": {
        "vi": "Số điện thoại phải từ 7 đến 14 chữ số.",
        "en": "Phone must contain 7 to 14 digits.",
    },
    "err_address_len": {
        "vi": "Địa chỉ không được vượt quá 255 ký tự.",
        "en": "Address must be 255 characters or fewer.",
    },
    "err_password_required": {
        "vi": "Mật khẩu không được để trống.",
        "en": "Password is required.",
    },
    "check_details": {
        "vi": "Vui lòng kiểm tra lại",
        "en": "Check your details",
    },
    "signing_in": {
        "vi": "Đang đăng nhập…",
        "en": "Signing in…",
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
        "vi": "Tổng quan",
        "en": "Dashboard",
    },
    "nav_booking": {
        "vi": "Đặt lịch",
        "en": "Book Appointment",
    },
    "nav_appointments": {
        "vi": "Lịch khám",
        "en": "Appointments",
    },
    "nav_profile": {
        "vi": "Hồ sơ",
        "en": "My Profile",
    },
    "nav_medical_history": {
        "vi": "Bệnh án",
        "en": "Medical History",
    },
    "nav_invoice_history": {
        "vi": "Hóa đơn",
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
        "vi": "Tiếp tục",
        "en": "Continue",
    },
    "spec_divider_lbl": {
        "vi": "Hoặc bấm chọn trực tiếp chuyên khoa bên dưới:",
        "en": "Or select directly from the specialties below:",
    },
    "select_this_specialty": {
        "vi": "Chọn chuyên khoa",
        "en": "Select specialty",
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
        "vi": "Đổi chuyên khoa",
        "en": "Change specialty",
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
        "vi": "Chọn bác sĩ",
        "en": "Select doctor",
    },
    "no_doctors_found": {
        "vi": "Không có bác sĩ nào cho chuyên khoa này",
        "en": "No doctors found for this specialty",
    },
    "step_3_back": {
        "vi": "Đổi bác sĩ",
        "en": "Change doctor",
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
        "vi": "Đổi giờ khám",
        "en": "Change time slot",
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
        "vi": "Xác nhận đặt lịch",
        "en": "Confirm Booking",
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
        "vi": "Đặt lịch mới",
        "en": "Book Appointment",
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
    # Status Badges & Filters
    # --------------------------------------------------------------------------
    "status_pending": {"vi": "Chờ xác nhận", "en": "Pending"},
    "status_confirmed": {"vi": "Đã xác nhận", "en": "Confirmed"},
    "status_checked_in": {"vi": "Đã tiếp nhận", "en": "Checked In"},
    "status_in_progress": {"vi": "Đang khám", "en": "In Progress"},
    "status_completed": {"vi": "Hoàn tất", "en": "Completed"},
    "status_cancelled": {"vi": "Đã hủy", "en": "Cancelled"},
    "status_paid": {"vi": "Đã thanh toán", "en": "Paid"},
    "status_unpaid": {"vi": "Chưa thanh toán", "en": "Unpaid"},
    "status_all": {"vi": "Tất cả", "en": "All"},

    # --------------------------------------------------------------------------
    # Common Actions & Dialogs
    # --------------------------------------------------------------------------
    "btn_refresh": {"vi": "Làm mới", "en": "Refresh"},
    "btn_view_details": {"vi": "Xem chi tiết", "en": "View Details"},
    "btn_edit": {"vi": "Chỉnh sửa", "en": "Edit"},
    "btn_save": {"vi": "Lưu thay đổi", "en": "Save Changes"},
    "btn_cancel_action": {"vi": "Hủy", "en": "Cancel"},
    "btn_back": {"vi": "Quay lại", "en": "Back"},
    "btn_filter": {"vi": "Lọc", "en": "Filter"},
    "loading": {"vi": "Đang tải...", "en": "Loading..."},
    "processing": {"vi": "Đang xử lý...", "en": "Processing..."},

    # --------------------------------------------------------------------------
    # Dashboard
    # --------------------------------------------------------------------------
    "dashboard_greeting": {"vi": "Xin chào, {name}", "en": "Hello, {name}"},
    "dashboard_greeting_default": {"vi": "Xin chào", "en": "Hello"},
    "dashboard_subtitle": {
        "vi": "Tổng quan chăm sóc sức khỏe và lịch khám sắp tới.",
        "en": "Here is an overview of your care and your next visit.",
    },
    "care_overview": {"vi": "Tổng quan sức khỏe", "en": "Care overview"},
    "stat_appointments": {"vi": "Lịch khám", "en": "Appointments"},
    "stat_medical_records": {"vi": "Hồ sơ bệnh án", "en": "Medical Records"},
    "stat_invoices": {"vi": "Hóa đơn viện phí", "en": "Invoices"},
    "stat_unpaid_invoices": {"vi": "Chưa thanh toán", "en": "Unpaid Invoices"},
    "upcoming_appointment": {"vi": "Lịch hẹn sắp tới", "en": "Upcoming appointment"},
    "next_visit": {"vi": "Lịch khám kế tiếp", "en": "Your next visit"},
    "no_upcoming_title": {"vi": "Không có lịch hẹn sắp tới", "en": "No upcoming appointments"},
    "no_upcoming_desc": {
        "vi": "Lịch khám đã xác nhận tiếp theo sẽ hiển thị tại đây.",
        "en": "Your next confirmed visit will appear here when one is scheduled.",
    },
    "field_doctor": {"vi": "Bác sĩ", "en": "Doctor"},
    "field_specialty": {"vi": "Chuyên khoa", "en": "Specialty"},
    "field_clinic": {"vi": "Phòng khám", "en": "Clinic"},
    "field_date": {"vi": "Ngày khám", "en": "Date"},
    "field_start_time": {"vi": "Giờ bắt đầu", "en": "Start time"},
    "field_end_time": {"vi": "Giờ kết thúc", "en": "End time"},
    "field_time": {"vi": "Khung giờ", "en": "Time"},
    "field_reason": {"vi": "Lý do khám", "en": "Reason"},

    # --------------------------------------------------------------------------
    # Medical History & Result
    # --------------------------------------------------------------------------
    "medical_history_title": {"vi": "Lịch sử bệnh án", "en": "Medical History"},
    "medical_history_subtitle": {
        "vi": "Xem lại chẩn đoán, ghi chú lâm sàng và kết quả khám.",
        "en": "Review diagnoses, clinical notes, and care from previous visits.",
    },
    "medical_search_placeholder": {
        "vi": "Tìm kiếm theo chẩn đoán, triệu chứng, bác sĩ...",
        "en": "Search diagnosis, symptoms, doctor, or specialty",
    },
    "th_exam_date": {"vi": "Ngày khám", "en": "Examination Date"},
    "th_diagnosis": {"vi": "Chẩn đoán", "en": "Diagnosis"},
    "no_records_found": {"vi": "Không tìm thấy hồ sơ bệnh án", "en": "No medical records found"},
    "no_records_desc": {
        "vi": "Thử đổi từ khóa tìm kiếm hoặc làm mới danh sách.",
        "en": "Try a different search term or refresh to check for new records.",
    },
    "records_count": {"vi": "Tìm thấy {count} hồ sơ bệnh án", "en": "{count} medical records found"},
    "medical_result_title": {"vi": "Kết quả khám bệnh", "en": "Medical Result"},
    "medical_result_subtitle": {
        "vi": "Chi tiết kết quả chẩn đoán và đơn thuốc đã kê.",
        "en": "A read-only summary of your examination and prescription.",
    },
    "btn_view_appointment": {"vi": "Xem lịch khám", "en": "View appointment"},
    "sec_exam_summary": {"vi": "Thông tin ca khám", "en": "Examination summary"},
    "field_symptoms": {"vi": "Triệu chứng", "en": "Symptoms"},
    "field_clinical_notes": {"vi": "Ghi chú lâm sàng", "en": "Clinical notes"},
    "sec_prescription": {"vi": "Đơn thuốc", "en": "Prescription"},
    "th_medicine": {"vi": "Tên thuốc", "en": "Medicine"},
    "th_quantity": {"vi": "Số lượng", "en": "Quantity"},
    "th_dosage": {"vi": "Liều dùng", "en": "Dosage"},
    "th_instructions": {"vi": "Cách dùng", "en": "Instructions"},
    "no_prescription_title": {"vi": "Không có đơn thuốc", "en": "No prescription"},
    "no_prescription_desc": {
        "vi": "Không có thuốc nào được kê cho ca khám này.",
        "en": "No medication was prescribed for this examination.",
    },

    # --------------------------------------------------------------------------
    # Invoices & Invoice Details
    # --------------------------------------------------------------------------
    "invoice_history_title": {"vi": "Lịch sử hóa đơn", "en": "Invoice History"},
    "invoice_history_subtitle": {
        "vi": "Theo dõi chi phí và trạng thái thanh toán viện phí.",
        "en": "Track charges and payment status for your clinic visits.",
    },
    "filter_by_status": {"vi": "Lọc theo trạng thái thanh toán", "en": "Narrow results by payment status"},
    "th_invoice_num": {"vi": "Mã hóa đơn", "en": "Invoice"},
    "th_total_amount": {"vi": "Tổng tiền", "en": "Total Amount"},
    "no_invoices_found": {"vi": "Không tìm thấy hóa đơn", "en": "No invoices found"},
    "no_invoices_desc": {
        "vi": "Thử đổi trạng thái lọc hoặc làm mới danh sách.",
        "en": "Try another payment status or refresh to check for new invoices.",
    },
    "invoices_count": {"vi": "Tìm thấy {count} hóa đơn", "en": "{count} invoices found"},
    "invoice_detail_title": {"vi": "Chi tiết hóa đơn", "en": "Invoice Detail"},
    "invoice_detail_subtitle": {
        "vi": "Xem chi tiết dịch vụ, tổng tiền và thanh toán.",
        "en": "Review billed services, totals, and payment information.",
    },
    "btn_view_medical_result": {"vi": "Kết quả khám", "en": "Medical result"},
    "btn_view_invoice": {"vi": "Hóa đơn", "en": "Invoice"},
    "sec_invoice_summary": {"vi": "Thông tin hóa đơn", "en": "Invoice summary"},
    "sec_invoice_items": {"vi": "Chi tiết dịch vụ", "en": "Billed services"},
    "th_service_name": {"vi": "Tên dịch vụ", "en": "Service"},
    "th_price": {"vi": "Đơn giá", "en": "Price"},
    "th_line_total": {"vi": "Thành tiền", "en": "Total"},
    "sec_payment_info": {"vi": "Thông tin thanh toán", "en": "Payment information"},
    "field_status": {"vi": "Trạng thái", "en": "Status"},
    "field_appointment_status": {"vi": "Trạng thái", "en": "Status"},
    "field_payment_status": {"vi": "Trạng thái thanh toán", "en": "Payment status"},
    "field_payment_method": {"vi": "Phương thức", "en": "Payment method"},
    "field_payment_date": {"vi": "Thời gian thanh toán", "en": "Payment date"},
    "payment_pending_title": {"vi": "Chưa thanh toán", "en": "Payment pending"},
    "payment_pending_desc": {
        "vi": "Hóa đơn này hiện chưa có giao dịch thanh toán nào được ghi nhận.",
        "en": "No payment has been recorded for this invoice yet.",
    },

    # --------------------------------------------------------------------------
    # Appointment History & Details
    # --------------------------------------------------------------------------
    "appointment_history_title": {"vi": "Lịch hẹn khám", "en": "Appointment History"},
    "appointment_history_subtitle": {
        "vi": "Theo dõi và quản lý các lịch hẹn khám sắp tới và trước đây.",
        "en": "Find and review your upcoming and previous clinic visits.",
    },
    "appointment_search_placeholder": {
        "vi": "Tìm kiếm bác sĩ, chuyên khoa, phòng khám...",
        "en": "Search doctor, specialty, clinic, or reason",
    },
    "no_appointments_found": {"vi": "Không tìm thấy lịch hẹn", "en": "No appointments found"},
    "no_appointments_desc": {
        "vi": "Thử đổi từ khóa tìm kiếm hoặc trạng thái lọc.",
        "en": "Try changing the search text or status filter, then refresh the list.",
    },
    "appointments_count": {"vi": "Tìm thấy {count} lịch hẹn", "en": "{count} appointments found"},
    "appointment_detail_subtitle": {
        "vi": "Xem lại thông tin lịch khám, bác sĩ phụ trách và cơ sở.",
        "en": "Review the visit, care provider, and clinic information.",
    },
    "sec_appointment_summary": {"vi": "Thông tin lịch khám", "en": "Appointment summary"},
    "btn_medical_result": {"vi": "Bệnh án", "en": "Medical Record"},
    "btn_invoice": {"vi": "Hóa đơn", "en": "Invoice"},

    # --------------------------------------------------------------------------
    # Patient Profile
    # --------------------------------------------------------------------------
    "profile_title": {"vi": "Hồ sơ bệnh nhân", "en": "My Profile"},
    "profile_subtitle": {
        "vi": "Quản lý thông tin cá nhân và liên hệ của bạn.",
        "en": "Keep your personal and contact information up to date.",
    },
    "sec_personal_info": {"vi": "Thông tin cá nhân", "en": "Personal information"},
    "sec_contact_info": {"vi": "Thông tin liên hệ", "en": "Contact details"},
    "account_notice": {"vi": "Tài khoản bệnh nhân", "en": "Your patient account"},
    "not_set": {"vi": "Chưa thiết lập", "en": "Not set"},

    # --------------------------------------------------------------------------
    # Date Picker & Calendar
    # --------------------------------------------------------------------------
    "btn_open_calendar": {"vi": "Chọn ngày", "en": "Select date"},
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
        "vi": "Chọn bác sĩ & giờ khám",
        "en": "Select doctor & slot",
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
