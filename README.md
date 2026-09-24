# Clinic Management System (Hệ Thống Quản Lý Phòng Khám)

Hệ thống quản lý phòng khám đa tầng hiện đại: giao diện máy tính để bàn (Desktop App) được xây dựng bằng **PySide6**, giao tiếp với máy chủ backend **FastAPI** thông qua giao thức HTTP/REST và xác thực JWT Bearer token; backend truy xuất cơ sở dữ liệu quan hệ **Microsoft SQL Server** thông qua **SQLAlchemy 2.0 ORM** và **ODBC Driver 18**.

Hệ thống hỗ trợ đầy đủ 4 nhóm vai trò (Role-Based Access Control): **Quản trị viên (ADMIN)**, **Bác sĩ (DOCTOR)**, **Bệnh nhân (PATIENT)**, và **Nhân viên tiếp đón / Thu ngân (STAFF)**.

---

## Mục lục

1. [Tổng quan hệ thống](#tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Mô hình cơ sở dữ liệu](#mô-hình-cơ-sở-dữ-liệu)
4. [Phạm vi chức năng theo vai trò](#phạm-vi-chức-năng-theo-vai-trò)
5. [Công nghệ sử dụng](#công-nghệ-sử-dụng)
6. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
7. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
8. [Hướng dẫn cài đặt và cấu hình](#hướng-dẫn-cài-đặt-và-cấu-hình)
9. [Khởi chạy ứng dụng](#khởi-chạy-ứng-dụng)
10. [Tài khoản thử nghiệm](#tài-khoản-thử-nghiệm)
11. [Danh mục API Reference](#danh-mục-api-reference)
12. [Kiểm thử và Đảm bảo chất lượng (Test Suite)](#kiểm-thử-và-đảm-bảo-chất-lượng-test-suite)
13. [Cẩm nang khắc phục sự cố](#cẩm-nang-khắc-phục-sự-cố)

---

## Tổng quan hệ thống

Clinic Management System cung cấp giải pháp toàn diện cho hoạt động khám chữa bệnh tại phòng khám tư nhân và đa khoa:
- **Bệnh nhân:** Tự đăng ký tài khoản, tra cứu danh mục phòng khám/chuyên khoa/bác sĩ, đặt lịch khám trực tuyến theo khung giờ trống, theo dõi tiến trình lịch hẹn, tra cứu lịch sử bệnh án điện tử, chi tiết đơn thuốc và theo dõi hóa đơn viện phí.
- **Bác sĩ:** Xem danh sách bệnh nhân được phân công trong ca trực, tiếp nhận bệnh nhân, nhập kết quả chẩn đoán/triệu chứng lâm sàng, kê đơn thuốc và hoàn tất hồ sơ khám bệnh.
- **Quản trị viên:** Quản lý tài khoản người dùng, phân quyền, cấu hình phòng khám, danh mục chuyên khoa, phân ca làm việc cho bác sĩ và xem báo cáo thống kê doanh thu, lưu lượng khám.
- **Tiếp đón & Thu ngân:** Tiếp đón bệnh nhân, thực hiện check-in vào phòng khám, phát hành hóa đơn viện phí và thu ngân (tiền mặt / thẻ).

---

## Kiến trúc hệ thống

Hệ thống tuân thủ kiến trúc đa tầng (Multi-tier Architecture) với ranh giới phân tách rõ ràng giữa giao diện, logic nghiệp vụ và truy xuất dữ liệu:

```text
+-----------------------------------------------------------------------------------+
|                        PySide6 Desktop Application                                |
|  - LoginWindow: Cửa sổ đăng nhập phân luồng tự động theo Role (Admin/Doctor/User) |
|  - Admin Dashboard: Quản trị User, Bác sĩ, Chuyên khoa, Phòng khám, Lịch trực     |
|  - Doctor Dashboard: Danh sách tiếp nhận, Khám bệnh, Chẩn đoán, Kê đơn thuốc      |
|  - Patient Portal (MainWindow): Dashboard, Đặt lịch, Lịch sử khám, Đơn thuốc      |
|  - API Client (httpx) & Bộ nhớ phiên (In-Memory Session State)                    |
+-----------------------------------------------------------------------------------+
                                          │
                                          │  HTTP / JSON + Bearer JWT
                                          ▼
+-----------------------------------------------------------------------------------+
|                              FastAPI REST Service                                 |
|  - API Routers: /auth, /patients, /appointments, /catalog, /medical-records,      |
|                 /invoices, /dashboard, /doctor, /users, /reception                |
|  - Security & Dependency Injection (CurrentPatient, CurrentUser, get_db)          |
|  - Pydantic v2 Request/Response Validation & Serialization                        |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                                 Service Layer                                     |
|  - BookingService, AppointmentService, PatientService, MedicalRecordService       |
|  - Kiểm tra quyền sở hữu dữ liệu (Ownership IDOR Enforcement)                     |
|  - Kiểm tra xung đột lịch hẹn, trạng thái hóa đơn và đơn thuốc                    |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                               Repository Layer                                    |
|  - Data Access Object (DAO) chuyên biệt cho từng thực thể                         |
|  - Xử lý eager loading (selectinload, joinedload) chống lỗi N+1 queries           |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                           SQLAlchemy 2.x Core & ORM                               |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼  pyodbc (ODBC Driver 18 for SQL Server)
+-----------------------------------------------------------------------------------+
|                             Microsoft SQL Server                                  |
|  - ClinicManagementDB (13 bảng quan hệ, Ràng buộc CHECK / FOREIGN KEY chặt chẽ)   |
+-----------------------------------------------------------------------------------+
```

### Cơ chế bảo mật và phân quyền (RBAC)

- **Chuẩn xác thực:** JWT Bearer Token (thuật toán HS256), băm mật khẩu chuẩn hiện đại Argon2 thông qua `pwdlib`.
- **Phân luồng giao diện:** Sau khi xác thực thành công, client đọc trường `role` trong payload để điều hướng trực tiếp vào giao diện tương ứng (Admin Dashboard, Doctor Dashboard hoặc Patient Portal).
- **Chống truy cập chéo dữ liệu (IDOR Protection):** Ở phía backend, mọi API của bệnh nhân đều ràng buộc với `CurrentPatient` (lấy `patient_id` từ token), ngăn chặn người dùng chỉnh sửa hoặc xem dữ liệu của bệnh nhân khác.
- **Ràng buộc trạng thái nghiệp vụ (State Machine):** Lịch hẹn chỉ có thể chuyển đổi tuần tự: `PENDING` ➔ `CONFIRMED` ➔ `CHECKED_IN` ➔ `IN_PROGRESS` ➔ `COMPLETED` (hoặc `CANCELLED`). Hóa đơn chỉ có thể thanh toán khi ở trạng thái `UNPAID`.

---

## Mô hình cơ sở dữ liệu

Tệp kịch bản DDL [`database/ClinicManagementDB.sql`](database/ClinicManagementDB.sql) định nghĩa cấu trúc hoàn chỉnh gồm 13 bảng quan hệ:

```text
+-------+       +----------+       +--------------+       +----------------+       +---------------+
| Users |-------| Patients |-------| Appointments |-------| MedicalRecords |-------| Prescriptions |
+-------+       +----------+       +--------------+       +----------------+       +---------------+
    |                                     |                                                |
    |                                     |                                        +------------------+
    |                                     |                                        | PrescriptionItems|
    |                                     |                                        +------------------+
    |                                     |
    |                                     |               +----------+       +--------------+
    |                                     +---------------| Invoices |-------| InvoiceItems |
    |                                     |               +----------+       +--------------+
    |                                     |                     |
    |                                     |               +----------+
    |                                     |               | Payments |
    |                                     |               +----------+
    |                                     |
    |           +-------------+           |
    +-----------|   Doctors   |-----------+
                +-------------+
                 |     |     |
     +-----------+     |     +-------------+
     |                 |                   |
+-------------+   +---------+    +-----------------+
| Specialties |   | Clinics |    | DoctorSchedules |
+-------------+   +---------+    +-----------------+
```

### Bảng tóm tắt danh mục thực thể

| Nhóm dữ liệu | Bảng | Chức năng chính | Ràng buộc quan trọng |
|---|---|---|---|
| **Người dùng & Phân quyền** | `Users` | Lưu tài khoản đăng nhập, password hash Argon2, vai trò. | `CK_Users_Role` (`PATIENT`, `DOCTOR`, `STAFF`, `ADMIN`), `UQ_Users_Username` |
| | `Patients` | Thông tin bệnh nhân (ngày sinh, giới tính, địa chỉ). | Khóa ngoại 1-1 với `Users(user_id)` |
| | `Doctors` | Thông tin bác sĩ, số chứng chỉ hành nghề, chuyên khoa, phòng khám. | Khóa ngoại 1-1 với `Users`, FK `Specialties`, FK `Clinics` |
| | `Specialties` | Danh mục chuyên khoa y tế (Nội khoa, Da liễu, Tim mạch,...). | `UQ_Specialties_Name` |
| | `Clinics` | Danh mục cơ sở khám chữa bệnh thực tế. | `clinic_name`, `address`, `phone` |
| | `DoctorSchedules` | Lịch trực định kỳ của bác sĩ theo thứ trong tuần và khung giờ. | `day_of_week` (1-7), `slot_duration` |
| **Lịch hẹn & Khám chữa bệnh** | `Appointments` | Lịch hẹn khám, bác sĩ phụ trách, cơ sở, thời gian. | `CK_Appointments_Status` (`PENDING`, `CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`) |
| | `MedicalRecords` | Hồ sơ bệnh án điện tử: triệu chứng, chẩn đoán, dặn dò. | Liên kết 1-1 với `Appointments` |
| | `Prescriptions` | Đơn thuốc xuất viện kèm theo bệnh án. | Liên kết 1-1 với `MedicalRecords` |
| | `PrescriptionItems` | Từng khoản mục thuốc trong đơn (tên thuốc, số lượng, liều dùng, HDSD). | `quantity > 0` |
| **Tài chính & Thu ngân** | `Invoices` | Hóa đơn viện phí theo lịch khám. | `CK_Invoices_Status` (`UNPAID`, `PAID`), `total_amount >= 0` |
| | `InvoiceItems` | Chi tiết các khoản phí dịch vụ y tế cấu thành hóa đơn. | `unit_price >= 0`, `quantity > 0` |
| | `Payments` | Giao dịch thanh toán viện phí thực tế. | `CK_Payments_Method` (`CASH`, `CARD`), `amount > 0` |

---

## Phạm vi chức năng theo vai trò

### 1. Phân hệ Bệnh nhân (Patient Portal)
- **Đăng ký & Đăng nhập:** Đăng ký tài khoản bệnh nhân mới trực tiếp từ client; đăng nhập nhận token JWT; tự động phục hồi phiên làm việc.
- **Bảng điều khiển cá nhân (Dashboard):** Tổng hợp lịch khám sắp tới, tổng số lượt khám, hóa đơn chưa thanh toán, lời khuyên sức khỏe.
- **Đặt lịch khám bệnh trực tuyến:**
  - Tra cứu theo phòng khám, chuyên khoa và bác sĩ phụ trách.
  - Chọn ngày khám và xem danh sách khung giờ trống (Available Slots) thực tế.
  - Điền lý do khám bệnh và gửi yêu cầu đặt lịch tức thời.
- **Quản lý lịch hẹn:**
  - Xem danh sách lịch hẹn cá nhân (phân trang, lọc theo trạng thái, tìm kiếm).
  - Đổi lịch khám (Reschedule) sang ngày/giờ khác.
  - Hủy lịch khám (Cancel) kèm lý do hủy (chỉ hủy được khi lịch chưa hoàn thành).
- **Hồ sơ bệnh án điện tử:**
  - Tra cứu toàn bộ lịch sử các lần khám bệnh.
  - Xem kết quả chẩn đoán, triệu chứng ghi nhận, ghi chú của bác sĩ.
  - Xem đơn thuốc điện tử chi tiết (tên thuốc, liều lượng, cách uống).
- **Hóa đơn & Lịch sử thanh toán:**
  - Xem danh sách hóa đơn viện phí theo trạng thái (`UNPAID` / `PAID`).
  - Xem chi tiết từng khoản mục chi phí y tế và biên lai thanh toán.
- **Cập nhật thông tin cá nhân:** Thay đổi số điện thoại, email, địa chỉ, ngày sinh, giới tính.

### 2. Phân hệ Bác sĩ (Doctor Portal)
- **Hồ sơ bác sĩ:** Xem thông tin chuyên khoa, số chứng chỉ hành nghề, cơ sở trực thuộc.
- **Lịch làm việc:** Xem lịch phân ca của bản thân theo các ngày trong tuần.
- **Quản lý bệnh nhân ca trực:** Xem danh sách các lịch hẹn bệnh nhân phân công cho mình (lọc theo ngày, trạng thái).
- **Khám bệnh & Bệnh án điện tử:**
  - Tiếp nhận bệnh nhân đang chờ khám.
  - Nhập triệu chứng lâm sàng, chẩn đoán bệnh án y khoa.
  - Kê đơn thuốc chi tiết: thêm thuốc, số lượng, liều dùng, hướng dẫn sử dụng.
  - Hoàn tất lượt khám (tự động chuyển trạng thái lịch hẹn sang `COMPLETED`).

### 3. Phân hệ Quản trị viên (Admin Portal)
- **Quản lý người dùng:** Thêm mới người dùng, xem danh sách, cập nhật thông tin, kích hoạt hoặc khóa tài khoản (`is_active`), phân quyền (`ADMIN`, `DOCTOR`, `PATIENT`, `STAFF`).
- **Quản lý bác sĩ:** Gán bác sĩ vào chuyên khoa và phòng khám, quản lý số giấy phép hành nghề.
- **Quản lý chuyên khoa:** Thêm, sửa, kích hoạt hoặc tạm dừng chuyên khoa khám bệnh.
- **Quản lý phòng khám:** Cập nhật thông tin cơ sở khám, địa chỉ, số điện thoại liên hệ.
- **Quản lý lịch làm việc:** Phân ca làm việc cho bác sĩ theo thứ và khung giờ làm việc.
- **Báo cáo thống kê:** Biểu đồ và chỉ số tổng quan về số lượng lịch hẹn, doanh thu, số lượt khám theo thời gian.

### 4. Phân hệ Tiếp đón & Thu ngân (Reception & Cashier)
- **Tiếp đón:** Tìm kiếm lịch hẹn bệnh nhân đến khám trong ngày, thực hiện Check-in (`CHECKED_IN`).
- **Lập hóa đơn & Thu ngân:** Tạo hóa đơn viện phí từ lịch khám đã hoàn thành, thực hiện ghi nhận thanh toán tiền mặt (`CASH`) hoặc quẹt thẻ (`CARD`).

---

## Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện | Phiên bản | Mục đích sử dụng |
|---|---|---|---|
| **Ngôn ngữ** | Python | >= 3.12 (khuyến nghị 3.12 / 3.14 x64) | Ngôn ngữ phát triển toàn diện cho cả Backend và Desktop App |
| **Backend Framework** | FastAPI | >= 0.115.0 | Web framework RESTful API hiện đại, bất đồng bộ, tốc độ cao |
| | Uvicorn | >= 0.30.0 | Máy chủ ASGI chạy API backend |
| | Pydantic v2 | >= 2.9.0 | Xác thực dữ liệu request/response theo schema chặt chẽ |
| **Cơ sở dữ liệu** | Microsoft SQL Server | 2019 / 2022 / Express | Hệ quản trị cơ sở dữ liệu quan hệ chính |
| | SQLAlchemy | >= 2.0.35 | ORM truy xuất dữ liệu nâng cao |
| | pyodbc | >= 5.2.0 | Kết nối Python với ODBC Driver của SQL Server |
| | MS ODBC Driver 18 | 18.x (x64) | Driver kết nối chính thức của Microsoft |
| **Bảo mật** | PyJWT | >= 2.9.0 | Ký và kiểm thực token JWT Bearer |
| | pwdlib [argon2] | >= 0.2.1 | Thuật toán băm mật khẩu chuẩn bảo mật cao |
| **Desktop Client** | PySide6 | >= 6.7.2 | Thư viện Qt for Python xây dựng giao diện máy tính để bàn |
| | httpx | >= 0.27.2 | HTTP client gửi yêu cầu đồng bộ/bất đồng bộ tới REST API |
| **Kiểm thử & Chất lượng**| pytest | >= 8.3.3 | Framework chạy kiểm thử tự động (Unit, Contract, Integration) |
| | Ruff | >= 0.7.0 | Công cụ kiểm tra linting và chuẩn hóa định dạng code |

---

## Cấu trúc thư mục

```text
ClinicManagement/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── deps.py             # Dependency injection (CurrentPatient, CurrentUser, Session)
│       │   └── routes/             # Tuyến đường API v1 theo domain nghiệp vụ
│       │       ├── appointments.py # Đặt lịch, hủy lịch, đổi lịch, tra cứu lịch hẹn
│       │       ├── auth.py         # Đăng ký, đăng nhập, thông tin tài khoản hiện tại
│       │       ├── catalog.py      # Tra cứu phòng khám, chuyên khoa, bác sĩ, slot trống
│       │       ├── dashboard.py    # Chỉ số thống kê nhanh cho bệnh nhân
│       │       ├── invoices.py     # Hóa đơn viện phí và chi tiết thanh toán
│       │       ├── medical_records.py # Bệnh án điện tử và đơn thuốc
│       │       ├── patients.py     # Hồ sơ cá nhân bệnh nhân
│       │       └── reception.py    # Tiếp đón bệnh nhân, check-in, lập hóa đơn và thu ngân
│       ├── core/
│       │   ├── clock.py            # Quản lý thời gian thống nhất theo múi giờ phòng khám
│       │   ├── config.py           # Cấu hình Pydantic BaseSettings, kiểm tra khóa bảo mật
│       │   ├── exceptions.py       # Bộ xử lý ngoại lệ tập trung chuẩn hóa phản hồi lỗi
│       │   └── security.py         # Mật khẩu Argon2 và mã hóa/giải mã JWT
│       ├── db/
│       │   ├── seed.py             # Kịch bản nạp dữ liệu mẫu an toàn (idempotent)
│       │   └── session.py          # Khởi tạo SQLAlchemy Engine và SessionLocal factory
│       ├── models/                 # Khai báo thực thể bảng (SQLAlchemy ORM 2.x)
│       ├── repositories/           # Tầng thao tác dữ liệu (Data Access Layer)
│       ├── routers/                # Các router bổ trợ (users, doctors, admin, doctor_portal)
│       ├── schemas/                # Schemas Pydantic v2 (Request, Response, Common)
│       ├── services/               # Tầng xử lý logic nghiệp vụ và xác thực phân quyền
│       └── main.py                 # Điểm khởi động chính của ứng dụng FastAPI
├── database/
│   └── ClinicManagementDB.sql      # Kịch bản DDL chuẩn tạo cơ sở dữ liệu và 13 bảng quan hệ
├── frontend/
│   ├── admin_dashboard.py          # Giao diện tổng thể dành cho Quản trị viên (ADMIN)
│   ├── app.py                      # Giao diện tổng thể dành cho Bác sĩ (DOCTOR)
│   ├── login_window.py             # Màn hình đăng nhập điều hướng tự động theo Role
│   ├── main_window.py              # Giao diện Cổng bệnh nhân (PATIENT PORTAL)
│   ├── main.py                     # Điểm khởi động ứng dụng Desktop PySide6
│   ├── api/                        # HTTP Client đóng gói kết nối và JWT
│   ├── core/                       # Cấu hình client và Session State lưu trữ trong RAM
│   ├── styles/                     # Bảng định kiểu Qt Style Sheet (.qss)
│   ├── views/                      # Các trang nghiệp vụ (Đặt lịch, Bệnh án, Hóa đơn,...)
│   └── widgets/                    # Các component UI tái sử dụng (Header, Badge, Banner,...)
├── script/
│   ├── init_run.ps1                # Script khởi tạo venv, .env và cài đặt toàn bộ thư viện tự động
│   ├── backend_run.ps1             # Script khởi động nhanh FastAPI backend
│   ├── frontend_run.ps1            # Script khởi động nhanh PySide6 desktop client
│   ├── seed_run.ps1                # Script nạp dữ liệu mẫu vào SQL Server
│   └── test_run.ps1                # Script chạy toàn bộ bộ kiểm thử tự động
├── tests/
│   ├── api/                        # Kiểm thử hợp đồng API (Mocked Contract Tests)
│   │   ├── test_booking_contract.py
│   │   ├── test_contract.py
│   │   ├── test_role_matrix.py     # Kiểm thử ma trận phân quyền 4 Roles
│   │   └── test_security_rbac.py   # Kiểm thử bảo mật, token giả mạo, IDOR
│   ├── integration/                # Kiểm thử tích hợp thật trên SQL Server (Auto Rollback)
│   │   └── test_sqlserver_flow.py
│   └── unit/                       # Kiểm thử đơn vị (Services, Schemas, Repositories, Client)
├── .env.example                    # Tệp mẫu cấu hình biến môi trường
├── pyproject.toml                  # Cấu hình pytest và Ruff
└── requirements.txt                # Danh sách gói phụ thuộc Python
```

---

## Yêu cầu hệ thống

Trước khi cài đặt, hãy đảm bảo máy tính đáp ứng các điều kiện sau:

1. **Hệ điều hành:** Microsoft Windows 10 hoặc Windows 11 (64-bit).
2. **Python:** Phiên bản Python 3.12 trở lên (kiểm tra bằng `python --version`).
3. **Cơ sở dữ liệu:** Microsoft SQL Server (bản 2019, 2022, Developer hoặc SQL Server Express).
4. **ODBC Driver:** **Microsoft ODBC Driver 18 for SQL Server (x64)** đã cài đặt trên Windows.
5. **Công cụ quản trị DB:** SQL Server Management Studio (SSMS) hoặc Azure Data Studio.

---

## Hướng dẫn cài đặt và cấu hình

### Cách nhanh nhất: Tự động khởi tạo bằng 1 lệnh

Khi vừa clone project về, mở PowerShell tại thư mục gốc và chạy:

```powershell
.\script\init_run.ps1
```

*(Script sẽ tự động: kiểm tra Python ➔ tạo môi trường ảo `venv` ➔ tạo file `.env` kèm `JWT_SECRET` bảo mật ➔ nâng cấp pip ➔ cài đặt toàn bộ thư viện trong `requirements.txt`).*

---

### Hoặc thực hiện thủ công từng bước:

#### Bước 1: Khởi tạo môi trường ảo và cài đặt thư viện

```powershell
# Tạo môi trường ảo
python -m venv venv

# Kích hoạt môi trường ảo
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1

# Nâng cấp pip và cài đặt thư viện phụ thuộc
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 2: Thiết lập tệp cấu hình môi trường (.env)

Sao chép từ tệp mẫu:

```powershell
Copy-Item .env.example .env
```

Mở tệp `.env` và điền thông số kết nối SQL Server và khóa bí mật JWT:

```dotenv
# Cấu hình Microsoft SQL Server
DB_HOST=localhost
DB_PORT=1433
DB_NAME=ClinicManagementDB
DB_USER=clinic_app
DB_PASSWORD=YourStrongPasswordHere!
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes

# Cấu hình bảo mật JWT (Bắt buộc >= 32 ký tự ngẫu nhiên)
JWT_SECRET=your_super_secret_jwt_random_key_min_32_chars_long
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Cấu hình kết nối API & Desktop Client
API_SCHEME=http
API_HOST=127.0.0.1
API_PORT=8000
API_TIMEOUT_SECONDS=15
CLINIC_TIMEZONE=Asia/Bangkok
```

> **Mẹo tạo khóa JWT ngẫu nhiên an toàn:**
> ```powershell
> python -c "import secrets; print(secrets.token_urlsafe(48))"
> ```

### Bước 3: Khởi tạo cơ sở dữ liệu (Database Schema)

1. Mở **SQL Server Management Studio (SSMS)** và kết nối tới SQL Server của bạn.
2. Mở file [`database/ClinicManagementDB.sql`](database/ClinicManagementDB.sql).
3. Nhấn **Execute** để tạo cơ sở dữ liệu `ClinicManagementDB` cùng 13 bảng và các ràng buộc dữ liệu toàn vẹn.
4. Đảm bảo tài khoản người dùng SQL (`DB_USER` trong `.env`) có quyền đọc/ghi trên cơ sở dữ liệu vừa tạo.

### Bước 4: Nạp dữ liệu mẫu (Seed Data)

Nạp dữ liệu mẫu để sẵn sàng kiểm thử:

```powershell
# Chạy script PowerShell có sẵn:
.\script\seed_run.ps1

# Hoặc thực thi module Python trực tiếp:
.\venv\Scripts\python.exe -m backend.app.db.seed
```

Kịch bản seed là **idempotent**, an toàn để chạy nhiều lần mà không bị lỗi trùng lặp dữ liệu.

---

## Khởi chạy ứng dụng

Hệ thống cung cấp sẵn các kịch bản PowerShell tiện lợi trong thư mục `script/`:

### 1. Khởi chạy máy chủ Backend API

Mở cửa sổ PowerShell thứ nhất:

```powershell
.\script\backend_run.ps1
```

*(Hoặc chạy lệnh thủ công: `.\venv\Scripts\uvicorn.exe backend.app.main:app --reload --host 127.0.0.1 --port 8000`)*

Các địa chỉ truy cập quan trọng:
- **Kiểm tra trạng thái máy chủ (Health Check):** <http://127.0.0.1:8000/health>
- **Tài liệu API tương tác (Swagger UI):** <http://127.0.0.1:8000/docs>
- **Tài liệu chuẩn OpenAPI (ReDoc):** <http://127.0.0.1:8000/redoc>

### 2. Khởi chạy ứng dụng Desktop Client

Mở một cửa sổ PowerShell thứ hai:

```powershell
.\script\frontend_run.ps1
```

*(Hoặc chạy lệnh thủ công: `.\venv\Scripts\python.exe -m frontend.main`)*

Cửa sổ đăng nhập sẽ hiển thị. Nhập tài khoản và mật khẩu, hệ thống sẽ tự động phân tích vai trò và mở giao diện tương ứng!

---

## Tài khoản thử nghiệm

Dữ liệu nạp mẫu (`seed.py`) tạo sẵn bộ tài khoản thử nghiệm đầy đủ cho tất cả 4 nhóm vai trò (Role):

| Vai trò (Role) | Tên đăng nhập | Mật khẩu | Họ và tên | Chuyên khoa / Đơn vị / Đặc điểm | Mục đích thử nghiệm |
|---|---|---|---|---|---|
| **Quản trị viên (ADMIN)** | `admin` | `Admin123!` | Quản trị viên hệ thống | Ban Giám đốc / IT | Quản lý người dùng, phân quyền, cấu hình bác sĩ, chuyên khoa, phòng khám, phân ca trực, xem báo cáo thống kê. |
| **Tiếp đón / Thu ngân (STAFF)** | `reception01` | `Staff123!` | Nguyễn Thị Mai | Cơ sở Quận 1 | Tiếp đón bệnh nhân, tra cứu lịch hẹn, thực hiện Check-in vào phòng khám, phát hành hóa đơn và ghi nhận thu ngân. |
| **Tiếp đón / Thu ngân (STAFF)** | `reception02` | `Staff123!` | Lê Hồng Hạnh | Cơ sở Tân Bình | Thử nghiệm nghiệp vụ tiếp đón và thu ngân đa chi nhánh. |
| **Bác sĩ (DOCTOR)** | `doctor01` | `Doctor123!` | BS. CKI Nguyễn Minh Anh | Nội tổng quát (Cơ sở Quận 1) | CCHN: `001245/HCM-CCHN`. Xem ca trực, tiếp nhận bệnh nhân, chẩn đoán Rối loạn lipid máu, kê đơn thuốc và hoàn tất khám. |
| **Bác sĩ (DOCTOR)** | `doctor02` | `Doctor123!` | ThS. BS Trần Thu Hà | Da liễu (Cơ sở Tân Bình) | CCHN: `003489/HCM-CCHN`. Khám Viêm da tiếp xúc dị ứng, mụn trứng cá, kê đơn kem bôi ngoài da. |
| **Bác sĩ (DOCTOR)** | `doctor03` | `Doctor123!` | BSCKII Lê Quang Huy | Tim mạch (Cơ sở Quận 1) | CCHN: `005612/HCM-CCHN`. Khám Tăng huyết áp nguyên phát, điện tâm đồ ECG, siêu âm Doppler tim. |
| **Bác sĩ (DOCTOR)** | `doctor04` | `Doctor123!` | ThS. BS Phạm Hoàng Nam | Tiêu hóa - Gan mật (Cơ sở Bình Thạnh) | CCHN: `007834/HCM-CCHN`. Khám Viêm dạ dày, trào ngược thực quản GERD, tiếp nhận bệnh nhân check-in trong ngày. |
| **Bác sĩ (DOCTOR)** | `doctor05` | `Doctor123!` | BS. CKI Đỗ Bích Thủy | Tai Mũi Họng (Cơ sở Quận 1) | CCHN: `009123/HCM-CCHN`. Khám Viêm amidan mủ, viêm xoang mũi cấp, chỉ định nội soi vòm họng. |
| **Bác sĩ (DOCTOR)** | `doctor06` | `Doctor123!` | BSCKII Hoàng Văn Thái | Cơ Xương Khớp (Cơ sở Tân Bình) | CCHN: `011456/HCM-CCHN`. Khám Thoái hóa khớp gối, tràn dịch khớp, đau mỏi vai gáy. |
| **Bệnh nhân (PATIENT)** | `patient01` | `Password123!` | Nguyễn Văn An (Nam, 1995) | Bình Thạnh, TP.HCM | **Tài khoản trọng điểm**: có lịch hẹn sắp tới (`CONFIRMED`), lịch sử nhiều đợt khám (`COMPLETED`), đơn thuốc, hóa đơn đã thanh toán (`PAID` - Thẻ & Tiền mặt) và hóa đơn chưa thanh toán (`UNPAID`). |
| **Bệnh nhân (PATIENT)** | `patient02` | `Password123!` | Trần Thị Bình (Nữ, 1998) | TP. Thủ Đức, TP.HCM | Bệnh nhân khám Tai Mũi Họng & Tiêu hóa, có ca `CHECKED_IN` tại phòng khám hôm nay. Dùng kiểm tra cách ly dữ liệu (IDOR). |
| **Bệnh nhân (PATIENT)** | `patient03` | `Password123!` | Lê Hoàng Long (Nam, 1982) | Quận 1, TP.HCM | Bệnh nhân tim mạch, có ca khám đang diễn ra (`IN_PROGRESS`). |
| **Bệnh nhân (PATIENT)** | `patient04` | `Password123!` | Phạm Thùy Linh (Nữ, 2001) | Quận 3, TP.HCM | Bệnh nhân sinh viên, có lịch hẹn mới đặt chờ duyệt (`PENDING`). |
| **Bệnh nhân (PATIENT)** | `patient05` | `Password123!` | Vũ Đình Trọng (Nam, 1965) | Tân Bình, TP.HCM | Bệnh nhân cao tuổi, lịch sử điều trị thoái hóa khớp gối và gout. |

---

## Danh mục API Reference

Toàn bộ các endpoint nghiệp vụ cá nhân đều yêu cầu header xác thực: `Authorization: Bearer <access_token>`.

### 1. Xác thực & Đăng nhập (Authentication)
| Phương thức | Endpoint | Quyền hạn | Mô tả |
|---|---|---|---|
| `POST` | `/auth/login` | Công khai | Đăng nhập bằng `OAuth2PasswordRequestForm` (hỗ trợ Desktop Client). |
| `POST` | `/api/v1/auth/login` | Công khai | Đăng nhập JSON payload, trả về access token. |
| `POST` | `/api/v1/auth/register` | Công khai | Đăng ký tài khoản bệnh nhân mới. |
| `GET` | `/api/v1/auth/me` | Bearer Token | Lấy thông tin định danh và vai trò của tài khoản đang đăng nhập. |

### 2. Danh mục & Lịch khám trống (Catalog)
| Phương thức | Endpoint | Tham số | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/catalog/clinics` | Không | Danh sách tất cả phòng khám đang hoạt động. |
| `GET` | `/api/v1/catalog/specialties` | Không | Danh sách tất cả chuyên khoa đang hoạt động. |
| `GET` | `/api/v1/catalog/doctors` | `specialty_id`, `clinic_id` | Tìm kiếm danh sách bác sĩ theo chuyên khoa hoặc phòng khám. |
| `GET` | `/api/v1/catalog/doctors/{id}/available-slots` | `date` (YYYY-MM-DD) | Lấy danh sách khung giờ trống thực tế của bác sĩ trong ngày. |

### 3. Cổng Bệnh nhân (Patient Portal Endpoints)
| Phương thức | Endpoint | Quyền hạn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/patients/me` | PATIENT | Tra cứu hồ sơ thông tin cá nhân. |
| `PATCH` | `/api/v1/patients/me` | PATIENT | Cập nhật số điện thoại, email, địa chỉ, ngày sinh, giới tính. |
| `POST` | `/api/v1/appointments` | PATIENT | Đặt lịch khám mới (kiểm tra chống spam và kiểm tra trùng slot). |
| `GET` | `/api/v1/appointments/me` | PATIENT | Danh sách lịch hẹn cá nhân (hỗ trợ phân trang, lọc trạng thái, tìm kiếm). |
| `GET` | `/api/v1/appointments/me/upcoming` | PATIENT | Lịch khám sắp tới gần nhất tính từ thời điểm hiện tại. |
| `GET` | `/api/v1/appointments/me/{id}` | PATIENT | Xem chi tiết lịch hẹn khám bệnh. |
| `PATCH` | `/api/v1/appointments/{id}/cancel` | PATIENT | Hủy lịch hẹn khám bệnh kèm lý do. |
| `PATCH` | `/api/v1/appointments/{id}/reschedule`| PATIENT | Dời lịch khám sang ngày và giờ khám mới. |
| `GET` | `/api/v1/medical-records/me` | PATIENT | Danh sách lịch sử hồ sơ bệnh án cá nhân. |
| `GET` | `/api/v1/medical-records/me/{id}`| PATIENT | Chi tiết bệnh án, chẩn đoán và đơn thuốc đã kê. |
| `GET` | `/api/v1/invoices/me` | PATIENT | Danh sách hóa đơn viện phí cá nhân (lọc `PAID`, `UNPAID`). |
| `GET` | `/api/v1/invoices/me/{id}` | PATIENT | Chi tiết hóa đơn, các khoản chi phí và biên lai thanh toán. |
| `GET` | `/api/v1/dashboard/me` | PATIENT | Chỉ số tổng quan dashboard cá nhân. |

### 4. Cổng Bác sĩ (Doctor Portal Endpoints)
| Phương thức | Endpoint | Quyền hạn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/doctor/profile` | DOCTOR | Xem thông tin chi tiết bác sĩ hiện tại. |
| `GET` | `/api/v1/doctor/schedules` | DOCTOR | Xem lịch phân ca của bác sĩ trong tuần. |
| `GET` | `/api/v1/doctor/appointments`| DOCTOR | Danh sách lịch hẹn bệnh nhân phân công cho bác sĩ (lọc ngày, trạng thái).|
| `POST` | `/api/v1/doctor/appointments/{id}/records` | DOCTOR | Nhập kết quả chẩn đoán, triệu chứng lâm sàng và hoàn thành khám. |
| `POST` | `/api/v1/doctor/prescriptions` | DOCTOR | Tạo đơn thuốc điện tử cho bệnh án vừa khám. |

### 5. Cổng Quản trị viên (Admin Portal Endpoints)
| Phương thức | Endpoint | Quyền hạn | Mô tả |
|---|---|---|---|
| `GET` / `POST` | `/api/v1/users` | ADMIN | Danh sách tài khoản người dùng / Tạo người dùng mới. |
| `GET` / `PUT` | `/api/v1/users/{id}` | ADMIN | Chi tiết người dùng / Cập nhật quyền và trạng thái hoạt động. |
| `GET` / `POST` | `/api/v1/doctors` | ADMIN | Quản lý thông tin hồ sơ bác sĩ, số chứng chỉ hành nghề. |
| `GET` / `POST` | `/api/v1/specialties` | ADMIN | Quản lý danh mục chuyên khoa. |
| `GET` / `POST` | `/api/v1/clinics` | ADMIN | Quản lý danh mục cơ sở phòng khám. |
| `GET` / `POST` | `/api/v1/schedules` | ADMIN | Quản lý lịch làm việc định kỳ của bác sĩ. |
| `GET` | `/api/v1/statistics` | ADMIN | Báo cáo thống kê tổng quan hệ thống. |

### 6. Tiếp đón & Thu ngân (Reception Endpoints)
| Phương thức | Endpoint | Quyền hạn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/reception/appointments` | STAFF, ADMIN | Danh sách lịch hẹn tiếp đón trong ngày. |
| `POST` | `/api/v1/reception/appointments/{id}/check-in` | STAFF, ADMIN | Check-in bệnh nhân vào phòng khám. |
| `POST` | `/api/v1/reception/invoices/{id}/pay` | STAFF, ADMIN | Ghi nhận thanh toán viện phí (`CASH` hoặc `CARD`). |

---

## Kiểm thử và Đảm bảo chất lượng (Test Suite)

Dự án áp dụng quy trình kiểm thử tự động nghiêm ngặt với tổng cộng **185 bài kiểm thử** bao phủ toàn bộ các tầng: Unit tests, Contract tests, RBAC Matrix tests và Live SQL Server Integration tests.

### 1. Chạy bộ kiểm thử tiêu chuẩn

Để chạy bộ kiểm thử mặc định (181 tests đơn vị & mock hợp đồng API):

```powershell
.\script\test_run.ps1
```

*(Hoặc chạy lệnh: `.\venv\Scripts\python.exe -m pytest -v`)*

Kết quả: **181 passed, 4 skipped, 0 warnings**.

### 2. Giải thích về 4 bài test bị SKIP và 0 Warning

- **Về 4 Skipped Tests:**
  - 4 bài kiểm thử nằm trong tệp `tests/integration/test_sqlserver_flow.py` là **kiểm thử tích hợp trực tiếp trên máy chủ SQL Server thật**.
  - Để tránh việc chạy test bị lỗi trong các môi trường CI/CD không có sẵn dịch vụ Microsoft SQL Server, pytest được cấu hình bỏ qua mặc định nếu chưa bật cờ môi trường.
  - Khi bật biến môi trường `RUN_SQLSERVER_INTEGRATION=1`, toàn bộ 4 bài test này sẽ kết nối trực tiếp vào database SQL Server thật, kiểm tra toàn diện luồng nghiệp vụ tạo lịch hẹn, khám bệnh, tạo bệnh án, xuất hóa đơn và thanh toán.
  - **Đảm bảo toàn vẹn dữ liệu:** Các test case tích hợp sử dụng cơ chế transaction savepoint (`create_savepoint`) và tự động rollback 100% sau khi chạy, **tuyệt đối không làm thay đổi hoặc phá hỏng dữ liệu demo hiện hữu**.
- **Về 0 Warning:**
  - Toàn bộ các cảnh báo deprecated của Pydantic V2 (`class Config` ➔ `model_config = ConfigDict(from_attributes=True)`) đã được xử lý triệt để.
  - Cảnh báo của Starlette TestClient đã được lọc chuẩn trong `pyproject.toml`. Bộ test hiện tại chạy hoàn toàn sạch sẽ không còn cảnh báo nào.

### 3. Chạy toàn bộ 185 tests (Bao gồm tích hợp SQL Server thật)

Mở PowerShell và chạy:

```powershell
$env:RUN_SQLSERVER_INTEGRATION="1"
.\venv\Scripts\python.exe -m pytest -v
Remove-Item Env:RUN_SQLSERVER_INTEGRATION
```

Kết quả thực tế:
```text
============================= 185 passed in 6.37s =============================
```
Tất cả 185/185 bài kiểm thử đều **PASS 100%**, với **0 lỗi, 0 skipped, 0 warnings**.

### 4. Kiểm tra Linting và chuẩn mã nguồn

```powershell
# Kiểm tra chuẩn cú pháp và import
.\venv\Scripts\ruff.exe check .

# Kiểm tra quy chuẩn định dạng code
.\venv\Scripts\ruff.exe format --check .
```

---

## Cẩm nang khắc phục sự cố

| Hiện tượng lỗi | Nguyên nhân khả dĩ | Giải pháp xử lý |
|---|---|---|
| `[WinError 10013] An attempt was made to access a socket...` | Cổng 8000 đang bị chiếm dụng bởi một tiến trình khác hoặc do dịch vụ mạng của Windows (như WinNAT, Hyper-V, ICS) giữ port. | 1. Đổi sang cổng khác, ví dụ cổng 8001: cập nhật `API_PORT=8001` trong `.env` và chạy backend với tham số `--port 8001`.<br>2. Hoặc tìm và tắt tiến trình đang chiếm port: `netstat -ano \| findstr :8000` sau đó `taskkill /PID <PID> /F`. |
| `Data source name not found, and no default driver specified` | Chưa cài Microsoft ODBC Driver 18 hoặc cấu hình sai tên driver trong `.env`. | Tải và cài đặt bản **Microsoft ODBC Driver 18 for SQL Server (x64)**. Kiểm tra giá trị `DB_DRIVER` trong `.env` phải đúng chính xác: `ODBC Driver 18 for SQL Server`. |
| `Login timeout expired` / Mã lỗi `08001` / Connection refused | SQL Server chưa bật giao thức TCP/IP, cổng 1433 bị chặn bởi tường lửa, hoặc dịch vụ SQL Server chưa khởi chạy. | 1. Mở **SQL Server Configuration Manager**, chuyển trạng thái **TCP/IP** sang `Enabled`.<br>2. Khởi động lại dịch vụ SQL Server.<br>3. Kiểm tra kết nối bằng SSMS trước khi khởi động ứng dụng. |
| Lỗi chứng chỉ SSL: `SSL Provider: [error:0A000086:...]` | ODBC Driver 18 mặc định bật mã hóa và yêu cầu chứng chỉ máy chủ hợp lệ. | Với môi trường thử nghiệm cục bộ, đặt đồng thời `DB_ENCRYPT=yes` và `DB_TRUST_SERVER_CERTIFICATE=yes` trong tệp `.env`. |
| `Login failed for user 'clinic_app'` | Sai tài khoản/mật khẩu, chưa bật chế độ SQL Server Authentication, hoặc tài khoản chưa được gán quyền trên database. | 1. Trong SSMS, mở thuộc tính Server > mục **Security** > chọn **SQL Server and Windows Authentication mode**.<br>2. Kiểm tra tài khoản trong mục **Security > Logins**, đảm bảo có quyền `db_datareader` và `db_datawriter` trên database `ClinicManagementDB`. |
| Lỗi khởi động backend: `JWT_SECRET must be a private random value...` | Giá trị `JWT_SECRET` trong `.env` ngắn hơn 32 ký tự hoặc vẫn giữ nguyên chuỗi placeholder mẫu. | Tạo một chuỗi ngẫu nhiên mới bằng lệnh: `python -c "import secrets; print(secrets.token_urlsafe(48))"` và dán vào `JWT_SECRET`. |
| Lỗi hiển thị PySide6: `Could not find the Qt platform plugin "windows"` | Xung đột môi trường ảo hoặc cài đặt thiếu thư viện PySide6 trong `.venv`. | Đảm bảo môi trường ảo `.venv` đã được kích hoạt đúng trước khi chạy. Thực hiện cài đặt lại bằng lệnh: `pip install --force-reinstall PySide6`. |