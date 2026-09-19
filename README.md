# Clinic Management System

Ứng dụng quản lý phòng khám tập trung vào cổng bệnh nhân. Hệ thống gồm một desktop app
PySide6 giao tiếp với FastAPI qua HTTP/JSON và JWT; backend truy cập cơ sở dữ liệu Microsoft
SQL Server hiện hữu bằng SQLAlchemy 2.x và `pyodbc`.

## Chức năng

- Đăng ký tài khoản bệnh nhân, đăng nhập bằng username, đăng xuất và xem phiên hiện tại.
- Xem/cập nhật hồ sơ bệnh nhân.
- Xem, tìm kiếm, lọc và phân trang lịch hẹn; xem lịch hẹn sắp tới và chi tiết lịch hẹn.
- Xem lịch sử khám, kết quả khám và đơn thuốc.
- Xem lịch sử hóa đơn, các dòng chi tiết và thông tin thanh toán ở chế độ chỉ đọc.
- Dashboard tổng hợp số liệu và lịch hẹn sắp tới.
- Phân quyền theo JWT; mọi tài nguyên riêng tư được giới hạn theo bệnh nhân hiện tại.

Các thao tác đặt/sửa/hủy lịch hẹn, xử lý thanh toán, cổng bác sĩ và cổng quản trị không thuộc
phạm vi phiên bản này.

## Kiến trúc

```text
PySide6 desktop app
        │ HTTP/JSON + JWT
        ▼
FastAPI routers
        ▼
Service layer
        ▼
Repository layer
        ▼
SQLAlchemy 2.x + pyodbc
        ▼
Microsoft SQL Server
```

Frontend không kết nối trực tiếp tới SQL Server. Backend dùng session theo từng request và
không tự gọi `create_all()`, drop hoặc tái tạo schema khi khởi động.

## Tổng quan cơ sở dữ liệu

[`database/ClinicManagementDB.sql`](database/ClinicManagementDB.sql) là nguồn sự thật của
schema. Script tạo 13 bảng:

```text
Users ─┬─ Patients ─ Appointments ─┬─ MedicalRecords ─ Prescriptions ─ PrescriptionItems
       │                            └─ Invoices ─┬─ InvoiceItems
       └─ Doctors ─┬─ Specialties              └─ Payments
                   ├─ Clinics
                   └─ DoctorSchedules
```

Không đổi tên bảng/cột hoặc thêm trường giả trong ORM. Đặc biệt, thông tin cá nhân của bệnh
nhân/bác sĩ nằm trong `Users`; bệnh án và hóa đơn xác định bệnh nhân thông qua `Appointments`.

## Công nghệ

- Python 3.12
- PySide6 Qt Widgets, `httpx`
- FastAPI, Pydantic 2, pydantic-settings
- SQLAlchemy 2.x, `pyodbc`
- Microsoft SQL Server và Microsoft ODBC Driver 18 for SQL Server
- JWT (`PyJWT`) và mật khẩu Argon2 (`pwdlib`)
- pytest và Ruff

## Cấu trúc thư mục

```text
ClinicManagement/
├── backend/
│   └── app/
│       ├── api/             # dependencies và API routers
│       ├── core/            # settings, security, exception handling
│       ├── db/              # session factory và seed
│       ├── models/          # SQLAlchemy mappings
│       ├── repositories/    # truy vấn dữ liệu
│       ├── schemas/         # Pydantic request/response models
│       ├── services/        # nghiệp vụ
│       └── main.py          # FastAPI application
├── database/
│   └── ClinicManagementDB.sql
├── frontend/
│   ├── api/                 # API client và background workers
│   ├── core/                # client config và in-memory session
│   ├── styles/              # shared QSS
│   ├── views/               # patient screens
│   ├── widgets/             # shared Qt widgets
│   └── main.py
├── tests/                   # unit/API tests không thay DB bằng SQLite
├── .env.example
├── pyproject.toml
└── requirements.txt
```

## Yêu cầu hệ thống

- Windows 10/11.
- Python 3.12 (xác nhận bằng `py -3.12 --version`).
- Microsoft SQL Server và SQL Server Management Studio (SSMS).
- Microsoft ODBC Driver 18 for SQL Server, đúng kiến trúc 64-bit của Python.
- Tài khoản SQL Server có quyền đọc/ghi trên database `ClinicManagementDB`.

## Cài đặt

Mở PowerShell tại thư mục project:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Nếu PowerShell chặn activation script, có thể cho phép script trong riêng process hiện tại:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Cấu hình môi trường

Tạo file local `.env` từ mẫu (file này đã được gitignore):

```powershell
Copy-Item .env.example .env
```

Cập nhật tối thiểu các giá trị sau trong `.env`:

```dotenv
DB_HOST=localhost
DB_PORT=1433
DB_NAME=ClinicManagementDB
DB_USER=clinic_app
DB_PASSWORD=your_real_password
DB_DRIVER=ODBC Driver 18 for SQL Server
DB_ENCRYPT=yes
DB_TRUST_SERVER_CERTIFICATE=yes
JWT_SECRET=replace_with_a_long_random_secret
CLINIC_TIMEZONE=Asia/Bangkok
API_SCHEME=http
API_HOST=127.0.0.1
API_PORT=8000
API_TIMEOUT_SECONDS=15
```

Tạo một khóa JWT riêng (không dùng nguyên placeholder trong file mẫu), rồi dán kết quả vào
`JWT_SECRET`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Backend từ chối khởi động nếu `JWT_SECRET` ngắn hơn 32 ký tự hoặc vẫn là placeholder.
`CLINIC_TIMEZONE` dùng tên múi giờ IANA và quyết định ngày/giờ hiện tại khi kiểm tra lịch hẹn
sắp tới, ngày sinh và dữ liệu seed.

`DB_TRUST_SERVER_CERTIFICATE=yes` thuận tiện cho môi trường phát triển dùng chứng chỉ local.
Với production, cài chứng chỉ hợp lệ và cân nhắc đặt giá trị này thành `no`. Không commit `.env`.
Nếu SQL Server local dùng default instance qua Shared Memory thay vì TCP, có thể đặt
`DB_PORT=none`; trên môi trường triển khai nên cấu hình TCP và port cụ thể.

## Tạo database

1. Mở SSMS và kết nối tới SQL Server đích.
2. Mở `database/ClinicManagementDB.sql`.
3. Kiểm tra server đích rồi chạy toàn bộ script đúng một lần.
4. Xác nhận database `ClinicManagementDB` có đủ 13 bảng.
5. Tạo/cấp quyền tài khoản ứng dụng khớp `DB_USER` và `DB_PASSWORD` trong `.env` nếu cần.

Ứng dụng không tự tạo schema và không được dùng `Base.metadata.create_all()` thay cho script.
Không chạy test tích hợp trên database production hoặc database chứa dữ liệu cần bảo toàn.

## Seed dữ liệu demo

Sau khi tạo schema và cấu hình `.env`:

```powershell
python -m backend.app.db.seed
```

Seed được thiết kế để có thể chạy lại mà không nhân bản các bản ghi nhận diện được. Nếu lệnh
không kết nối được, kiểm tra dịch vụ SQL Server, TCP/IP, port, ODBC Driver và thông tin đăng nhập.
Chỉ chạy seed trên database local/demo/test: để giữ tài khoản demo đăng nhập được, seed chủ động
đưa các bản ghi mang username demo và dữ liệu liên quan về trạng thái mẫu xác định.

## Chạy backend

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Các địa chỉ hữu ích:

- Health check: <http://127.0.0.1:8000/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

Health check thành công trả về tối thiểu:

```json
{"status": "ok"}
```

## Chạy desktop app

Giữ backend đang chạy, mở PowerShell thứ hai, activate cùng virtual environment rồi chạy:

```powershell
.\.venv\Scripts\Activate.ps1
python -m frontend.main
```

Desktop app ghép base URL từ `API_SCHEME`, `API_HOST` và `API_PORT`; cấu hình mặc định gọi
`http://127.0.0.1:8000`. JWT chỉ được giữ trong bộ nhớ; ứng dụng không lưu password hoặc token
xuống ổ đĩa.

## Tài khoản demo

Các tài khoản được tạo bởi seed:

| Tài khoản | Username | Password | Mục đích |
|---|---|---|---|
| Patient A | `patient01` | `Password123!` | Luồng demo chính |
| Patient B | `patient02` | `Password123!` | Kiểm tra ownership/cách ly dữ liệu |

Password trong bảng `Users` được lưu dưới dạng Argon2 hash, không phải plaintext. Hãy đổi mật
khẩu demo nếu dùng ngoài môi trường học tập/local.

## Kiểm tra chất lượng

Các unit/API test dùng mock và FastAPI dependency overrides, không thay application database
layer bằng SQLite:

```powershell
pytest -q
ruff check .
python -m compileall backend frontend
```

Test tích hợp SQL Server phải chạy trên database test riêng và được đánh dấu `integration`.
Chúng mặc định được bỏ qua để tránh ghi nhầm vào database không dành cho test. Chạy rõ ràng bằng:

```powershell
$env:RUN_SQLSERVER_INTEGRATION="1"
pytest -q tests/integration
Remove-Item Env:RUN_SQLSERVER_INTEGRATION
```

Có thể loại chúng khỏi một lượt kiểm tra local bằng:

```powershell
pytest -q -m "not integration"
```

## API chính

Tất cả endpoint riêng tư dùng Bearer token:

```text
POST  /api/v1/auth/register
POST  /api/v1/auth/login
GET   /api/v1/auth/me
GET   /api/v1/patients/me
PATCH /api/v1/patients/me
GET   /api/v1/appointments/me
GET   /api/v1/appointments/me/upcoming
GET   /api/v1/appointments/me/{appointment_id}
GET   /api/v1/medical-records/me
GET   /api/v1/medical-records/me/{medical_record_id}
GET   /api/v1/invoices/me
GET   /api/v1/invoices/me/{invoice_id}
GET   /api/v1/dashboard/me
GET   /health
```

## Khắc phục sự cố

### `No suitable Python runtime found` với `py -3.12`

Cài Python 3.12 x64 từ python.org, bật Python Launcher trong installer, mở terminal mới rồi chạy
lại `py -0p`. Không dùng nhầm Python 3.11/3.14 cho môi trường project đã chốt ở 3.12.

### `Data source name not found` hoặc không tìm thấy ODBC driver

Cài **Microsoft ODBC Driver 18 for SQL Server x64** và xác nhận tên trong `.env` đúng chính xác:
`ODBC Driver 18 for SQL Server`. Khởi động lại terminal sau khi cài.

### Login timeout / `08001` / connection refused

Kiểm tra dịch vụ SQL Server đang chạy, bật TCP/IP trong SQL Server Configuration Manager, xác
nhận port 1433/firewall, `DB_HOST`, instance name và SQL authentication. Thử kết nối cùng thông
tin bằng SSMS trước.

### Lỗi chứng chỉ ODBC Driver 18

Môi trường local có thể dùng `DB_ENCRYPT=yes` cùng `DB_TRUST_SERVER_CERTIFICATE=yes`. Production
nên dùng chứng chỉ tin cậy thay vì tắt kiểm tra chứng chỉ.

### `Login failed for user`

Xác nhận SQL authentication đã bật, login tồn tại, password đúng và login đã được map/cấp quyền
trên `ClinicManagementDB`. Không đưa password thật vào log, issue hoặc commit.

### Backend chạy nhưng desktop báo offline

Mở `/health`, kiểm tra `API_SCHEME`, `API_HOST`, `API_PORT` và firewall. Nếu backend chạy ở
host/port khác, sửa các giá trị tương ứng trong `.env` rồi khởi động lại desktop app.

### Qt không khởi động hoặc lỗi platform plugin

Đảm bảo virtual environment đang active và `PySide6` được cài trong chính environment đó. Không
copy thủ công thư mục Qt từ Python installation khác; cài lại bằng `pip install -r requirements.txt`.
