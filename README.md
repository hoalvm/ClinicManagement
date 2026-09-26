# Clinic Management System

Hệ thống quản lý phòng khám toàn diện, được thiết kế theo kiến trúc phân tầng hiện đại:
- **Backend:** Dịch vụ RESTful API xây dựng trên nền tảng **FastAPI**, **SQLAlchemy 2.0 ORM** và **Pydantic v2**.
- **Database:** **Microsoft SQL Server** với ràng buộc toàn vẹn dữ liệu chặt chẽ, kết nối qua **ODBC Driver 18**.
- **Frontend:** Ứng dụng máy tính để bàn (Desktop App) giao diện đồ họa hiện đại bằng **PySide6 (Qt Python)**.

---

## Phân hệ chức năng theo vai trò

Hệ thống hỗ trợ 4 nhóm người dùng chính:

1. **Quản trị viên (ADMIN):**
   - Quản lý tài khoản người dùng, phân quyền và khóa/kích hoạt tài khoản.
   - Quản lý danh mục bác sĩ, chuyên khoa, cơ sở phòng khám và phân ca trực.
   - Theo dõi báo cáo thống kê tổng quan (doanh thu, lượt khám, lưu lượng bệnh nhân).

2. **Bác sĩ (DOCTOR):**
   - Theo dõi danh sách bệnh nhân theo ca trực.
   - Kê đơn thuốc với định lượng, liều dùng và hướng dẫn chi tiết.
   - Tiếp nhận bệnh nhân, ghi nhận triệu chứng lâm sàng và chẩn đoán bệnh án điện tử.

3. **Tiếp đón & Thu ngân (STAFF):**
   - Đặt lịch khám và điều chỉnh lịch hẹn cho bệnh nhân tại quầy.
   - Tiếp đón bệnh nhân, thực hiện check-in vào phòng khám theo số thứ tự.
   - Xuất hóa đơn viện phí, ghi nhận thanh toán tiền mặt (CASH) hoặc chuyển khoản/thẻ (CARD).

4. **Bệnh nhân (PATIENT):**
   - Đăng ký và quản lý thông tin hồ sơ cá nhân.
   - Theo dõi tiến trình lịch hẹn, dời lịch hoặc hủy lịch khi cần.
   - Đặt lịch khám trực tuyến theo cơ sở, chuyên khoa, bác sĩ và khung giờ trống thực tế.
   - Tra cứu lịch sử khám bệnh, xem kết quả chẩn đoán, đơn thuốc điện tử và hóa đơn viện phí.

---

## Cấu trúc thư mục

```text
ClinicManagement/
|-- backend/
|   `-- app/
|       |-- api/            # API routes và dependency injection
|       |-- core/           # Cấu hình, bảo mật JWT/Argon2, xử lý ngoại lệ
|       |-- db/             # Kết nối cơ sở dữ liệu và kịch bản nạp dữ liệu (seed)
|       |-- models/         # Khai báo thực thể bảng SQLAlchemy ORM
|       |-- repositories/   # Tầng truy xuất dữ liệu (Data Access Layer)
|       |-- schemas/        # Định nghĩa lược đồ dữ liệu Pydantic
|       |-- services/       # Tầng xử lý logic nghiệp vụ
|       `-- main.py         # Điểm khởi chạy FastAPI backend
|-- database/
|   `-- ClinicManagementDB.sql # Kịch bản khởi tạo cơ sở dữ liệu và 13 bảng quan hệ
|-- frontend/
|   |-- api/                # Client HTTP đóng gói gọi API backend
|   |-- core/               # Quản lý phiên làm việc (Session) và đa ngôn ngữ (i18n)
|   |-- views/              # Các màn hình chức năng chi tiết
|   |-- widgets/            # Thành phần giao diện tái sử dụng
|   |-- admin_dashboard.py  # Giao diện Quản trị viên
|   |-- app.py              # Giao diện Bác sĩ
|   |-- reception_dashboard.py # Giao diện Tiếp đón & Thu ngân
|   |-- main_window.py      # Giao diện Cổng bệnh nhân
|   |-- login_window.py     # Cửa sổ đăng nhập điều hướng tự động
|   `-- main.py             # Điểm khởi chạy ứng dụng Desktop
|-- script/                 # Các tập lệnh PowerShell hỗ trợ vận hành nhanh
|-- tests/                  # Bộ kiểm thử tự động (Unit, Contract, Integration)
|-- .env.example            # Tệp mẫu cấu hình môi trường
`-- requirements.txt        # Danh sách thư viện phụ thuộc
```

---

## Cài đặt và Khởi chạy

### 1. Cài đặt tự động
Tại thư mục gốc dự án, mở PowerShell và chạy:

```powershell
.\script\init_run.ps1
```

Script sẽ tự động tạo môi trường ảo `venv`, cài đặt thư viện phụ thuộc và sinh tệp cấu hình `.env`.

*(Nếu cài đặt thủ công: chạy `python -m venv venv`, kích hoạt venv và thực hiện `pip install -r requirements.txt`).*

### 2. Nạp dữ liệu mẫu (Seed Data)
Chạy script nạp dữ liệu mẫu (an toàn, có thể chạy lại nhiều lần):

```powershell
.\script\seed_run.ps1
```

### 3. Khởi chạy hệ thống
- **Khởi chạy Backend:**
  ```powershell
  .\script\backend_run.ps1
  ```
  Tài liệu API Swagger UI có sẵn tại: `http://127.0.0.1:8000/docs`

- **Khởi chạy Frontend (Giao diện đăng nhập tập trung):**
  ```powershell
  .\script\frontend_run.ps1
  ```
  Hệ thống sẽ tự động nhận diện vai trò tài khoản sau khi đăng nhập và mở đúng Dashboard tương ứng.

---

## Tài khoản thử nghiệm

Dữ liệu nạp mẫu cung cấp sẵn các tài khoản thử nghiệm cho từng vai trò:

| Vai trò | Tên đăng nhập | Mật khẩu | Thông tin bổ sung |
|---|---|---|---|
| Quản trị viên (ADMIN) | `admin` | `Admin123!` | Quản trị viên hệ thống |
| Bác sĩ (DOCTOR) | `doctor01` | `Doctor123!` | BS. CKI Nguyễn Minh Anh (Nội tổng quát, Cơ sở Q1) |
| Bác sĩ (DOCTOR) | `doctor02` | `Doctor123!` | ThS. BS Trần Thu Hà (Da liễu, Cơ sở Tân Bình) |
| Tiếp đón / Thu ngân (STAFF) | `reception01` | `Staff123!` | Nguyễn Thị Mai (Tiếp đón & Thu ngân Q1) |
| Bệnh nhân (PATIENT) | `patient01` | `Password123!` | Nguyễn Văn An (Đã có sẵn lịch hẹn, bệnh án, hóa đơn) |
| Bệnh nhân (PATIENT) | `patient02` | `Password123!` | Trần Thị Bình (Tài khoản thử nghiệm bảo mật IDOR) |