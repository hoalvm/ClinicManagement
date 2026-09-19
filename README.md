# Clinic Management System

Hệ thống quản lý phòng khám được xây dựng theo kiến trúc phân tầng hiện đại: frontend được phát triển bằng **PySide6** giao tiếp với máy chủ backend **FastAPI** thông qua giao thức HTTP/REST và xác thực JWT, backend truy xuất cơ sở dữ liệu quan hệ **Microsoft SQL Server** thông qua **SQLAlchemy**.

---

## Mục lục

1. [Tổng quan hệ thống](#tổng-quan-hệ-thống)
2. [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
3. [Mô hình cơ sở dữ liệu](#mô-hình-cơ-sở-dữ-liệu)
4. [Phạm vi chức năng](#phạm-vi-chức-năng)
5. [Công nghệ sử dụng](#công-nghệ-sử-dụng)
6. [Cấu trúc thư mục](#cấu-trúc-thư-mục)
7. [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
8. [Hướng dẫn cài đặt và cấu hình](#hướng-dẫn-cài-đặt-và-cấu-hình)
9. [Khởi chạy ứng dụng](#khởi-chạy-ứng-dụng)
10. [Tài khoản thử nghiệm](#tài-khoản-thử-nghiệm)
11. [Danh mục API Reference](#danh-mục-api-reference)
12. [Kiểm thử và Đảm bảo chất lượng](#kiểm-thử-và-đảm-bảo-chất-lượng)
13. [Cẩm nang khắc phục sự cố](#cẩm-nang-khắc-phục-sự-cố)

---

## Tổng quan hệ thống

Hệ thống tập trung tối ưu hóa trải nghiệm tự phục vụ của bệnh nhân, cho phép người dùng tra cứu lịch sử khám bệnh, theo dõi đơn thuốc, quản lý hóa đơn và thông tin cá nhân một cách minh bạch, an toàn và tức thời.

## Kiến trúc hệ thống

Hệ thống tuân thủ mô hình đa tầng (Multi-tier Architecture) với ranh giới phân tách rõ ràng giữa giao diện, logic nghiệp vụ và truy xuất dữ liệu:

```text
+-------------------------------------------------------------+
|                  PySide6 Desktop Application                |
|  - Views (QStackedWidget, Patient Pages)                    |
|  - Components (Sidebar, FeedbackBanner, StatusBadge, etc.)  |
|  - API Client (httpx) & In-Memory Session State             |
+-------------------------------------------------------------+
                              │
                              │  HTTP / JSON + Bearer JWT
                              ▼
+-------------------------------------------------------------+
|                     FastAPI REST Service                    |
|  - API Router & Dependency Injection (Security / DB Session)|
|  - Pydantic v2 Request/Response Validation                  |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                        Service Layer                        |
|  - Nghiệp vụ bệnh nhân, lịch hẹn, hồ sơ y tế, hóa đơn       |
|  - Kiểm tra quyền sở hữu dữ liệu (Ownership Enforcement)    |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                      Repository Layer                       |
|  - Truy vấn dữ liệu chuyên biệt theo từng thực thể          |
+-------------------------------------------------------------+
                              │
                              ▼
+-------------------------------------------------------------+
|                  SQLAlchemy 2.x Core & ORM                  |
+-------------------------------------------------------------+
                              │
                              ▼  pyodbc (ODBC Driver 18)
+-------------------------------------------------------------+
|                    Microsoft SQL Server                     |
|  - ClinicManagementDB (13 bảng quan hệ)                     |
+-------------------------------------------------------------+
```

### Cơ chế quản lý phiên và cách ly dữ liệu

- **Xác thực:** Chuẩn JWT Bearer Token (thuật toán HS256), băm mật khẩu bằng Argon2 thông qua thư viện `pwdlib`.
- **Cách ly dữ liệu:** Toàn bộ API nghiệp vụ đều yêu cầu phụ thuộc `CurrentPatient`. Người dùng đang đăng nhập chỉ có thể xem và tương tác với các dữ liệu gắn liền với `PatientID` của chính mình. Mọi hành vi truy cập chéo dữ liệu đều bị từ chối ở tầng Service.

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

### Phân nhóm thực thể

| Nhóm dữ liệu | Bảng | Chức năng chính |
|---|---|---|
| **Người dùng & Phân quyền** | `Users` | Lưu trữ tài khoản người dùng, mã hash Argon2, thông tin định danh và vai trò (`PATIENT`, `DOCTOR`, `STAFF`, `ADMIN`). |
| | `Patients` | Mở rộng thông tin bệnh nhân (ngày sinh, giới tính, địa chỉ) liên kết 1-1 với `Users`. |
| | `Doctors` | Mở rộng thông tin bác sĩ, số chứng chỉ hành nghề, chuyên khoa và phòng khám trực thuộc. |
| | `Specialties` | Danh mục chuyên khoa y tế (Nội khoa, Da liễu, Tim mạch,...). |
| | `Clinics` | Danh mục cơ sở/phòng khám thực tế. |
| | `DoctorSchedules` | Lịch làm việc định kỳ của bác sĩ theo ngày trong tuần và khung giờ. |
| **Lịch hẹn & Khám chữa bệnh** | `Appointments` | Thông tin lịch khám, thời gian, trạng thái (`PENDING`, `CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`). |
| | `MedicalRecords` | Bệnh án điện tử sau khi khám, ghi nhận triệu chứng, chẩn đoán và dặn dò của bác sĩ. |
| | `Prescriptions` | Đơn thuốc gắn liền với hồ sơ khám bệnh. |
| | `PrescriptionItems` | Chi tiết từng loại thuốc trong đơn (tên thuốc, số lượng, liều lượng, cách dùng). |
| **Tài chính & Thanh toán** | `Invoices` | Hóa đơn viện phí phát sinh theo lịch khám (`UNPAID`, `PAID`). |
| | `InvoiceItems` | Chi tiết khoản mục chi phí (tiền khám, xét nghiệm, thủ thuật,...). |
| | `Payments` | Giao dịch thanh toán viện phí (`CASH`, `CARD`). |

---

## Phạm vi chức năng

### Phân hệ bệnh nhân (In-Scope)

- **Xác thực & Phiên làm việc:**
  - Đăng ký tài khoản bệnh nhân mới với các trường kiểm tra tính hợp lệ chặt chẽ.
  - Đăng nhập xác thực bằng tài khoản và mật khẩu, cấp phát access token.
  - Xem thông tin tài khoản hiện hành và tự động đăng xuất an toàn khi phiên làm việc hết hạn.
- **Quản lý thông tin cá nhân:**
  - Tra cứu hồ sơ bệnh nhân hiện hành.
  - Cập nhật số điện thoại, email, địa chỉ, ngày sinh và giới tính.
- **Tra cứu lịch hẹn khám bệnh:**
  - Xem danh sách lịch hẹn cá nhân hỗ trợ phân trang (`page`, `page_size`).
  - Tìm kiếm linh hoạt theo từ khóa (tên bác sĩ, chuyên khoa, phòng khám).
  - Lọc theo trạng thái lịch hẹn (`PENDING`, `CONFIRMED`, `CHECKED_IN`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).
  - Xem chi tiết từng lịch hẹn và hiển thị chỉ báo lịch hẹn sắp diễn ra.
- **Hồ sơ bệnh án và Đơn thuốc:**
  - Xem lịch sử các đợt khám bệnh đã hoàn tất.
  - Tra cứu chi tiết bệnh án: triệu chứng lâm sàng, chẩn đoán y khoa, lời khuyên của bác sĩ.
  - Xem danh mục đơn thuốc chi tiết: tên biệt dược, liều lượng, số lượng và hướng dẫn sử dụng.
- **Hóa đơn và Lịch sử thanh toán:**
  - Tra cứu danh sách hóa đơn theo trạng thái (`PAID`, `UNPAID`).
  - Xem chi tiết từng hóa đơn, danh sách dịch vụ y tế cấu thành tổng tiền.
  - Xem thông tin giao dịch thanh toán (ngày thanh toán, số tiền, hình thức tiền mặt hoặc thẻ).
- **Bảng điều khiển tổng quan (Dashboard):**
  - Thống kê tổng số lịch hẹn, hồ sơ bệnh án, hóa đơn chờ xử lý.
  - Widget nổi bật nhắc nhở lịch khám sắp tới gần nhất.

### Giới hạn phạm vi (Out-of-Scope)

Các nghiệp vụ sau không thuộc phạm vi triển khai của phiên bản này:
- Cổng dành cho bác sĩ (khám bệnh, kê đơn thuốc, nhập chẩn đoán).
- Cổng dành cho quản trị viên và nhân viên lễ tân (xếp lịch, phân ca, tiếp đón, thu ngân).
- Cổng tích hợp thanh toán trực tuyến qua ngân hàng/ví điện tử (hệ thống hiện tại ghi nhận giao dịch tại quầy).
- Tự đặt lịch hoặc hủy lịch chủ động từ phía bệnh nhân (dữ liệu lịch hẹn hiện tại được cung cấp ở chế độ tra cứu sau khi phòng khám xếp lịch).

---

## Công nghệ sử dụng

| Thành phần | Công nghệ / Thư viện | Phiên bản | Mục đích sử dụng |
|---|---|---|---|
| **Ngôn ngữ** | Python | 3.12 (64-bit) | Nền tảng thực thi thống nhất cho backend và frontend |
| **Backend API** | FastAPI | >= 0.115.0 | Web framework hiệu năng cao xây dựng RESTful API |
| | Uvicorn | >= 0.30.0 | Máy chủ ASGI phục vụ API |
| | Pydantic / Pydantic Settings | >= 2.9.0 | Kiểm thực dữ liệu schema và quản lý biến môi trường |
| **Cơ sở dữ liệu** | Microsoft SQL Server | 2019 / 2022 | Hệ quản trị cơ sở dữ liệu quan hệ chính |
| | SQLAlchemy | >= 2.0.35 | ORM và biểu thức SQL nâng cao |
| | pyodbc | >= 5.2.0 | Kết nối Python với ODBC Driver của SQL Server |
| | MS ODBC Driver 18 | 18.x (x64) | Trình điều khiển kết nối cơ sở dữ liệu |
| **Bảo mật** | PyJWT | >= 2.9.0 | Ký và xác thực JSON Web Token |
| | pwdlib [argon2] | >= 0.2.1 | Thuật toán băm mật khẩu an toàn theo tiêu chuẩn hiện đại |
| **Desktop Client** | PySide6 | >= 6.7.2 | Bộ công cụ Qt Widgets xây dựng giao diện người dùng |
| | httpx | >= 0.27.2 | HTTP client bất đồng bộ / đồng bộ giao tiếp REST API |
| **Kiểm thử & CI** | pytest | >= 8.3.3 | Framework chạy kiểm thử tự động |
| | Ruff | >= 0.7.0 | Linter và code formatter tốc độ cao |

---

## Cấu trúc thư mục

```text
ClinicManagement/
├── backend/
│   └── app/
│       ├── api/
│       │   ├── deps.py             # Dependency injection (CurrentPatient, CurrentUser, Session)
│       │   └── routes/             # Định tuyến API phân theo domain nghiệp vụ
│       │       ├── appointments.py
│       │       ├── auth.py
│       │       ├── dashboard.py
│       │       ├── invoices.py
│       │       ├── medical_records.py
│       │       └── patients.py
│       ├── core/
│       │   ├── clock.py            # Quản lý thời gian thống nhất theo múi giờ phòng khám
│       │   ├── config.py           # Cấu hình Pydantic BaseSettings, kiểm tra khóa bảo mật
│       │   ├── exceptions.py       # Bộ xử lý ngoại lệ tập trung chuẩn hóa phản hồi lỗi
│       │   └── security.py         # Xử lý mật khẩu Argon2 và mã hóa/giải mã JWT
│       ├── db/
│       │   ├── seed.py             # Kịch bản nạp dữ liệu mẫu an toàn (idempotent)
│       │   └── session.py          # Khởi tạo SQLAlchemy Engine và SessionLocal factory
│       ├── models/                 # Khai báo thực thể bảng cơ sở dữ liệu (SQLAlchemy ORM)
│       ├── repositories/           # Tầng thao tác dữ liệu (Data Access Layer)
│       ├── schemas/                # Khai báo schema Pydantic (Request, Response, Pagination)
│       ├── services/               # Tầng xử lý logic nghiệp vụ và xác thực phân quyền
│       └── main.py                 # Điểm khởi động ứng dụng FastAPI
├── database/
│   └── ClinicManagementDB.sql      # Kịch bản DDL chuẩn tạo cơ sở dữ liệu và 13 bảng quan hệ
├── frontend/
│   ├── api/
│   │   ├── api_client.py           # HTTP Client đóng gói lời gọi API và quản lý Bearer Token
│   │   └── workers.py              # Luồng nền xử lý tác vụ mạng tránh treo giao diện Qt
│   ├── core/
│   │   ├── config.py               # Cấu hình kết nối API cho giao diện người dùng
│   │   └── session.py              # Trạng thái phiên người dùng lưu trong bộ nhớ RAM
│   ├── styles/
│   │   └── main.qss                # Bảng định kiểu tập trung (Qt Style Sheet)
│   ├── ui/
│   │   └── icons.py                # Bộ hiển thị biểu tượng vector giao diện
│   ├── views/                      # Màn hình giao diện nghiệp vụ bệnh nhân
│   │   ├── appointment_detail_view.py
│   │   ├── appointment_history_view.py
│   │   ├── dashboard_view.py
│   │   ├── invoice_detail_view.py
│   │   ├── invoice_history_view.py
│   │   ├── login_view.py
│   │   ├── medical_history_view.py
│   │   ├── medical_result_view.py
│   │   ├── patient_profile_view.py
│   │   └── register_view.py
│   ├── widgets/                    # Các thành phần giao diện dùng chung (Reusable UI Components)
│   │   ├── empty_state.py
│   │   ├── feedback_banner.py
│   │   ├── loading_indicator.py
│   │   ├── page_header.py
│   │   ├── pagination.py
│   │   ├── sidebar.py
│   │   ├── stat_card.py
│   │   └── status_badge.py
│   ├── main_window.py              # Cửa sổ chính điều phối chuyển trang và ngăn kéo điều hướng
│   └── main.py                     # Điểm khởi động ứng dụng máy tính để bàn PySide6
├── tests/
│   ├── api/                        # Kiểm thử hợp đồng API với TestClient và mock
│   ├── integration/                # Kiểm thử tích hợp thực tế với SQL Server (tự rollback)
│   ├── unit/                       # Kiểm thử đơn vị các module services, schemas, repositories
│   └── conftest.py
├── .env.example                    # Tệp mẫu thiết lập biến môi trường
├── pyproject.toml                  # Cấu hình Ruff và pytest
└── requirements.txt                # Danh sách gói phụ thuộc của dự án
```

---

## Yêu cầu hệ thống

Trước khi cài đặt, hãy đảm bảo máy tính đáp ứng đầy đủ các điều kiện tiên quyết sau:

1. **Hệ điều hành:** Microsoft Windows 10 hoặc Windows 11 (phiên bản 64-bit).
2. **Môi trường Python:** Python 3.12 (kiểm tra bằng lệnh `py -3.12 --version` hoặc `python --version`).
3. **Cơ sở dữ liệu:** Microsoft SQL Server (bản 2019, 2022, Developer Edition hoặc SQL Server Express).
4. **Trình điều khiển kết nối:** **Microsoft ODBC Driver 18 for SQL Server (x64)** đã được cài đặt vào hệ thống.
5. **Công cụ quản trị cơ sở dữ liệu:** SQL Server Management Studio (SSMS) hoặc Azure Data Studio / `sqlcmd`.

---

## Hướng dẫn cài đặt và cấu hình

### Bước 1: Khởi tạo môi trường ảo và cài đặt thư viện

Mở PowerShell tại thư mục gốc của dự án:

```powershell
# Tạo môi trường ảo sử dụng Python 3.12
py -3.12 -m venv .venv

# Kích hoạt môi trường ảo (cho phép chạy script nếu có chính sách chặn)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# Nâng cấp pip và cài đặt toàn bộ gói phụ thuộc
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 2: Thiết lập tệp cấu hình môi trường (.env)

Tạo tệp `.env` cục bộ từ tệp mẫu:

```powershell
Copy-Item .env.example .env
```

Mở tệp `.env` vừa tạo và cập nhật các thông số phù hợp với môi trường làm việc của bạn:

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

# Cấu hình bảo mật JWT
JWT_SECRET=replace_with_a_long_random_secret_generated_below
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Cấu hình API và Desktop Client
API_SCHEME=http
API_HOST=127.0.0.1
API_PORT=8000
API_TIMEOUT_SECONDS=15
CLINIC_TIMEZONE=Asia/Bangkok
```

#### Chi tiết tham số cấu hình

| Biến môi trường | Kiểu dữ liệu | Mặc định | Mô tả chi tiết |
|---|---|---|---|
| `DB_HOST` | Chuỗi | `localhost` | Địa chỉ máy chủ lưu trữ cơ sở dữ liệu SQL Server. |
| `DB_PORT` | Số nguyên / Chuỗi | `1433` | Cổng TCP của SQL Server. Có thể đặt `none` nếu kết nối named instance cục bộ qua Shared Memory. |
| `DB_NAME` | Chuỗi | `ClinicManagementDB` | Tên cơ sở dữ liệu của hệ thống. |
| `DB_USER` | Chuỗi | `clinic_app` | Tài khoản đăng nhập SQL Server có quyền trên database. |
| `DB_PASSWORD` | Chuỗi bí mật | - | Mật khẩu tài khoản cơ sở dữ liệu (tuyệt đối không để mặc định). |
| `DB_DRIVER` | Chuỗi | `ODBC Driver 18 for SQL Server` | Tên chính xác của driver ODBC đã cài trên Windows. |
| `DB_ENCRYPT` | Chuỗi | `yes` | Mã hóa kênh truyền kết nối cơ sở dữ liệu. |
| `DB_TRUST_SERVER_CERTIFICATE`| Chuỗi | `yes` | Bỏ qua kiểm tra chứng chỉ SSL nội bộ cho môi trường phát triển local. |
| `JWT_SECRET` | Chuỗi bí mật | - | Khóa bí mật dùng ký JWT. **Bắt buộc có độ dài tối thiểu 32 ký tự** và không được chứa từ khóa mặc định. |
| `JWT_ALGORITHM` | Chuỗi | `HS256` | Thuật toán ký token. |
| `ACCESS_TOKEN_EXPIRE_MINUTES`| Số nguyên | `60` | Thời hạn hiệu lực của access token (phút). |
| `API_SCHEME` | Chuỗi | `http` | Giao thức kết nối giữa Desktop app và Backend (`http` hoặc `https`). |
| `API_HOST` | Chuỗi | `127.0.0.1` | Địa chỉ IP máy chủ API. |
| `API_PORT` | Số nguyên | `8000` | Cổng dịch vụ API. |
| `API_TIMEOUT_SECONDS` | Số thực | `15` | Thời gian chờ tối đa cho mỗi yêu cầu HTTP trước khi báo lỗi timeout. |
| `CLINIC_TIMEZONE` | Chuỗi | `Asia/Bangkok` | Tên múi giờ chuẩn IANA dùng để đồng bộ thời gian tính toán lịch hẹn. |

Tạo khóa bảo mật ngẫu nhiên cho biến `JWT_SECRET` bằng lệnh:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Sao chép chuỗi sinh ra và dán vào giá trị `JWT_SECRET` trong `.env`.

### Bước 3: Khởi tạo lược đồ cơ sở dữ liệu (Database Schema)

Hệ thống không dùng cơ chế tự động tạo bảng của ORM nhằm đảm bảo tính toàn vẹn và tối ưu khóa. Việc khởi tạo phải được thực hiện từ script SQL chính thức:

1. Mở công cụ **SQL Server Management Studio (SSMS)** và kết nối tới SQL Server đích.
2. Mở tệp kịch bản [`database/ClinicManagementDB.sql`](database/ClinicManagementDB.sql).
3. Thực thi kịch bản (Execute) một lần duy nhất. Kịch bản sẽ tạo cơ sở dữ liệu `ClinicManagementDB` cùng 13 bảng và các ràng buộc toàn vẹn dữ liệu.
4. Tạo tài khoản đăng nhập SQL Server (hoặc phân quyền cho tài khoản hiện có) tương ứng với giá trị `DB_USER` và `DB_PASSWORD` đã khai báo trong tệp `.env`.

### Bước 4: Nạp dữ liệu mẫu (Seed Data)

Sau khi cơ sở dữ liệu đã được tạo, tiến hành nạp dữ liệu mẫu phục vụ thử nghiệm và kiểm tra chức năng:

```powershell
python -m backend.app.db.seed
```

Kịch bản nạp dữ liệu được thiết kế an toàn (idempotent), có thể thực thi nhiều lần mà không tạo bản ghi trùng lặp và tự động cập nhật lại các chỉ số dữ liệu demo chuẩn hóa.

---

## Khởi chạy ứng dụng

### 1. Khởi chạy máy chủ Backend API

Mở cửa sổ PowerShell thứ nhất, kích hoạt môi trường ảo và chạy:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Các địa chỉ truy cập quan trọng:

- **Kiểm tra trạng thái máy chủ (Health Check):** <http://127.0.0.1:8000/health>
- **Tài liệu API tương tác (Swagger UI):** <http://127.0.0.1:8000/docs>
- **Tài liệu API chuẩn hóa (ReDoc):** <http://127.0.0.1:8000/redoc>
- **Lược đồ cấu trúc API (OpenAPI JSON):** <http://127.0.0.1:8000/openapi.json>

Khi máy chủ hoạt động bình thường, endpoint `/health` sẽ trả về:

```json
{
  "status": "ok"
}
```

### 2. Khởi chạy ứng dụng Desktop Client

Giữ máy chủ backend tiếp tục chạy, mở một cửa sổ PowerShell thứ hai, kích hoạt môi trường ảo và khởi động giao diện người dùng:

```powershell
.\.venv\Scripts\Activate.ps1
python -m frontend.main
```

Ứng dụng máy tính để bàn sẽ tự động kết nối tới địa chỉ API được định cấu hình trong `.env` (`http://127.0.0.1:8000`).

---

## Tài khoản thử nghiệm

Dữ liệu seed khởi tạo sẵn các tài khoản thử nghiệm sau:

| Loại tài khoản | Tên đăng nhập | Mật khẩu | Mục đích sử dụng |
|---|---|---|---|
| **Bệnh nhân A** | `patient01` | `Password123!` | Tài khoản chính kiểm thử toàn bộ luồng nghiệp vụ: xem dashboard, lịch sử khám bệnh nhiều chuyên khoa, đơn thuốc và hóa đơn. |
| **Bệnh nhân B** | `patient02` | `Password123!` | Tài khoản độc lập dùng để kiểm thử tính năng bảo vệ quyền sở hữu dữ liệu (đảm bảo không nhìn thấy hồ sơ của Bệnh nhân A). |
---

## Danh mục API Reference

Tất cả các endpoint nghiệp vụ cá nhân đều yêu cầu gửi kèm header xác thực `Authorization: Bearer <access_token>`.

### Nhóm Xác thực (Authentication)

| Phương thức | Đường dẫn | Quyền truy cập | Mô tả |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Công khai | Đăng ký tài khoản bệnh nhân mới (tạo bản ghi `Users` và `Patients`). |
| `POST` | `/api/v1/auth/login` | Công khai | Đăng nhập hệ thống, trả về JWT Access Token. |
| `GET` | `/api/v1/auth/me` | Bearer Token | Lấy thông tin định danh và vai trò của tài khoản đang đăng nhập. |

### Nhóm Hồ sơ bệnh nhân (Patients)

| Phương thức | Đường dẫn | Quyền truy cập | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/patients/me` | Bearer Token | Xem chi tiết hồ sơ bệnh nhân cá nhân (ngày sinh, giới tính, địa chỉ,...). |
| `PATCH` | `/api/v1/patients/me` | Bearer Token | Cập nhật thông tin hồ sơ bệnh nhân (họ tên, điện thoại, email, địa chỉ,...). |

### Nhóm Lịch hẹn (Appointments)

| Phương thức | Đường dẫn | Tham số truy vấn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/appointments/me` | `page` (int, default: 1)<br>`page_size` (int, default: 10)<br>`keyword` (str, optional)<br>`status` (enum, optional) | Lấy danh sách lịch hẹn cá nhân có phân trang, tìm kiếm và lọc trạng thái. |
| `GET` | `/api/v1/appointments/me/upcoming` | Không | Lấy thông tin lịch hẹn sắp tới gần nhất tính từ thời điểm hiện tại. |
| `GET` | `/api/v1/appointments/me/{appointment_id}` | `appointment_id` (int) | Xem chi tiết một lịch hẹn cụ thể (bác sĩ, phòng khám, ngày giờ, lý do). |

### Nhóm Hồ sơ bệnh án & Kết quả khám (Medical Records)

| Phương thức | Đường dẫn | Tham số truy vấn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/medical-records/me` | `page` (int, default: 1)<br>`page_size` (int, default: 10)<br>`keyword` (str, optional) | Tra cứu danh sách lịch sử bệnh án cá nhân có phân trang và tìm kiếm. |
| `GET` | `/api/v1/medical-records/me/{medical_record_id}` | `medical_record_id` (int) | Xem chi tiết kết quả khám, triệu chứng, chẩn đoán và đơn thuốc đi kèm. |

### Nhóm Hóa đơn viện phí (Invoices)

| Phương thức | Đường dẫn | Tham số truy vấn | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/invoices/me` | `page` (int, default: 1)<br>`page_size` (int, default: 10)<br>`status` (enum: `UNPAID`, `PAID`) | Tra cứu danh sách hóa đơn cá nhân có phân trang và lọc theo trạng thái. |
| `GET` | `/api/v1/invoices/me/{invoice_id}` | `invoice_id` (int) | Xem chi tiết hóa đơn, các khoản phí dịch vụ và giao dịch thanh toán. |

### Nhóm Tổng quan & Hệ thống (Dashboard & System)

| Phương thức | Đường dẫn | Quyền truy cập | Mô tả |
|---|---|---|---|
| `GET` | `/api/v1/dashboard/me` | Bearer Token | Lấy dữ liệu thống kê tổng quan và thông tin nhắc việc cho bệnh nhân. |
| `GET` | `/health` | Công khai | Kiểm tra tình trạng sẵn sàng của máy chủ API backend. |

---

## Kiểm thử và Đảm bảo chất lượng

Dự án áp dụng quy trình kiểm thử tự động nhiều tầng, kết hợp công cụ kiểm tra định dạng và chuẩn mã nguồn:

### 1. Chạy kiểm thử đơn vị và kiểm thử hợp đồng API (Mocked Tests)

Bộ kiểm thử đơn vị sử dụng `FastAPI TestClient` kết hợp `dependency_overrides` và mock dữ liệu, không tác động đến cơ sở dữ liệu thật:

```powershell
# Chạy toàn bộ kiểm thử đơn vị (loại trừ tích hợp)
pytest -q -m "not integration"
```

### 2. Chạy kiểm thử tích hợp với cơ sở dữ liệu thật (SQL Server Integration Tests)

Bộ kiểm thử tích hợp thực hiện các truy vấn thật trên Microsoft SQL Server. Mỗi test case được bao bọc trong một outer transaction và tự động rollback sau khi hoàn thành, đảm bảo **không làm thay đổi dữ liệu hiện hữu**:

```powershell
# Bật biến môi trường kích hoạt và chạy kiểm thử tích hợp
$env:RUN_SQLSERVER_INTEGRATION="1"
pytest -q tests/integration
Remove-Item Env:RUN_SQLSERVER_INTEGRATION
```

### 3. Kiểm tra định dạng và chuẩn mã nguồn (Linting & Formatting)

Sử dụng Ruff để kiểm tra chuẩn cú pháp (PEP 8, import, logic typing):

```powershell
# Kiểm tra lỗi lint
ruff check .

# Kiểm tra quy chuẩn định dạng code
ruff format --check .
```

### 4. Kiểm tra biên dịch bytecode

Đảm bảo không có lỗi cú pháp tiềm ẩn trong toàn bộ các tệp Python:

```powershell
python -m compileall backend frontend
```

---

## Cẩm nang khắc phục sự cố

| Hiện tượng lỗi | Nguyên nhân khả dĩ | Giải pháp xử lý |
|---|---|---|
| `No suitable Python runtime found` khi chạy `py -3.12` | Chưa cài đặt Python 3.12 hoặc chưa kích hoạt tính năng Windows Python Launcher. | Tải và cài đặt bản Python 3.12 x64 chính thức từ python.org, chọn tùy chọn **"Use developer features: Install launcher for all users"** trong trình cài đặt. |
| `Data source name not found, and no default driver specified` | Chưa cài Microsoft ODBC Driver 18 hoặc cấu hình sai tên driver trong `.env`. | Tải và cài đặt bản **Microsoft ODBC Driver 18 for SQL Server (x64)**. Kiểm tra giá trị `DB_DRIVER` trong `.env` phải đúng chính xác: `ODBC Driver 18 for SQL Server`. |
| `Login timeout expired` / Mã lỗi `08001` / Connection refused | SQL Server chưa bật giao thức TCP/IP, cổng 1433 bị chặn bởi tường lửa, hoặc dịch vụ chưa khởi chạy. | 1. Mở **SQL Server Configuration Manager**, chuyển trạng thái **TCP/IP** sang `Enabled`.<br>2. Khởi động lại dịch vụ SQL Server.<br>3. Kiểm tra kết nối từ xa bằng SSMS trước khi khởi động ứng dụng. |
| Lỗi xác thực chứng chỉ SSL: `SSL Provider: [error:0A000086:...]` | ODBC Driver 18 mặc định bật mã hóa và yêu cầu chứng chỉ máy chủ hợp lệ. | Với môi trường thử nghiệm cục bộ, đặt đồng thời `DB_ENCRYPT=yes` và `DB_TRUST_SERVER_CERTIFICATE=yes` trong tệp `.env`. |
| `Login failed for user 'clinic_app'` | Sai thông tin tài khoản, chưa bật chế độ SQL Server Authentication, hoặc tài khoản chưa được gán quyền trên database. | 1. Trong SSMS, mở thuộc tính Server > mục **Security** > chọn **SQL Server and Windows Authentication mode**.<br>2. Kiểm tra tài khoản trong thư mục **Security > Logins**, đảm bảo có quyền `db_datareader` và `db_datawriter` trên `ClinicManagementDB`. |
| Lỗi khởi động backend: `JWT_SECRET must be a private random value...` | Giá trị `JWT_SECRET` trong `.env` ngắn hơn 32 ký tự hoặc vẫn giữ nguyên chuỗi placeholder mẫu. | Tạo một chuỗi ngẫu nhiên mới bằng lệnh: `python -c "import secrets; print(secrets.token_urlsafe(48))"` và gán vào `JWT_SECRET`. |
| Giao diện Desktop hiển thị thông báo `Connection Error` hoặc mất kết nối | Backend chưa khởi chạy hoặc sai lệch cổng/địa chỉ giao tiếp. | 1. Kiểm tra máy chủ backend có đang chạy tại <http://127.0.0.1:8000/health> hay không.<br>2. Kiểm tra các giá trị `API_SCHEME`, `API_HOST`, `API_PORT` trong tệp `.env` đã đồng nhất giữa backend và client. |
| Lỗi khởi động Qt: `Could not find the Qt platform plugin "windows"` | Xung đột môi trường ảo hoặc cài đặt thiếu thư viện PySide6 trong `.venv`. | Đảm bảo môi trường ảo `.venv` đã được kích hoạt đúng trước khi chạy. Thực hiện cài đặt lại phụ thuộc bằng: `pip install --force-reinstall PySide6`. |
