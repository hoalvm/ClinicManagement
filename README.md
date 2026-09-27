# Clinic Management System

<p>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=flat-square&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat-square">
  <img src="https://img.shields.io/badge/Pydantic-v2-E92063?style=flat-square&logo=pydantic&logoColor=white">
  <img src="https://img.shields.io/badge/PySide6-Qt-41CD52?style=flat-square&logo=qt&logoColor=white">
  <img src="https://img.shields.io/badge/Microsoft_SQL_Server-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white">
</p>

Hệ thống quản lý phòng khám toàn diện, được thiết kế theo kiến trúc phân tầng hiện đại:
- **Frontend:** Desktop Application với thiết kế giao diện đồ họa hiện đại bằng **PySide6 (Qt with Python)**.
- **Backend:** Dịch vụ RESTful API xây dựng trên nền tảng **FastAPI**, **SQLAlchemy 2.0 ORM** và **Pydantic v2**.
- **Database:** Microsoft SQL Server với ràng buộc toàn vẹn dữ liệu chặt chẽ, kết nối thông qua **ODBC Driver 18**.

---

## Phân hệ chức năng theo vai trò

Hệ thống hỗ trợ 4 nhóm người dùng chính:

1. **Quản trị viên (Admin):**
   - Quản lý tài khoản người dùng, phân quyền và khóa/kích hoạt tài khoản.
   - Quản lý danh mục bác sĩ, chuyên khoa, cơ sở phòng khám và phân ca trực.
   - Theo dõi báo cáo thống kê tổng quan (doanh thu, lượt khám, lưu lượng bệnh nhân).

2. **Bác sĩ (Doctor):**
   - Theo dõi danh sách bệnh nhân theo ca trực.
   - Kê đơn thuốc với định lượng, liều dùng và hướng dẫn chi tiết.
   - Tiếp nhận bệnh nhân, ghi nhận triệu chứng lâm sàng và chẩn đoán bệnh án điện tử.

3. **Thu ngân (Staff):**
   - Tiếp nhận bệnh nhân vào phòng khám theo số thứ tự.
   - Đặt lịch khám và điều chỉnh lịch hẹn cho bệnh nhân tại quầy.
   - Xuất hóa đơn viện phí, ghi nhận thanh toán tiền mặt hoặc chuyển khoản.

4. **Bệnh nhân (Patient):**
   - Đăng ký và quản lý thông tin hồ sơ cá nhân.
   - Theo dõi tiến trình lịch hẹn, dời lịch hoặc hủy lịch khi cần.
   - Đặt lịch khám trực tuyến theo cơ sở, chuyên khoa, bác sĩ và khung giờ trống thực tế.
   - Tra cứu lịch sử khám bệnh, xem kết quả chẩn đoán, đơn thuốc điện tử và hóa đơn viện phí.

---

## Cài đặt khởi chạy

### 1. Cài đặt tự động

- **Khởi tạo ban đầu:**

```powershell
.\script\init_run.ps1
```

Script sẽ tự động tạo môi trường ảo `venv`, cài đặt thư viện phụ thuộc và sinh tệp cấu hình `.env`.

*(Nếu cài đặt thủ công: chạy `python -m venv venv`, kích hoạt venv và thực hiện `pip install -r requirements.txt`).*

### 2. Nạp dữ liệu mẫu

- **Nạp dữ liệu mẫu:**

```powershell
.\script\seed_run.ps1
```

### 3. Khởi chạy hệ thống

- **Khởi chạy Backend:**
  ```powershell
  .\script\backend_run.ps1
  ```

- **Khởi chạy Frontend:**
  ```powershell
  .\script\frontend_run.ps1
  ```

---

## Tài khoản thử nghiệm

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `Admin123!` |
| Doctor | `doctor01` | `Doctor123!` |
| Patient | `patient01` | `Password123!` |
| Reception | `reception01` | `Staff123!` |