from datetime import datetime, date, time
from backend.database import SessionLocal, engine, Base
from backend.models import User, Doctor, Patient, Appointment, AppointmentStatus
from backend.security import get_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Xóa dữ liệu cũ
db.query(Appointment).delete()
db.query(Patient).delete()
db.query(Doctor).delete()
db.query(User).delete()
db.commit()

# 1. Tạo User Bác sĩ Duy
user_doc = User(
    Username="bsduy",
    PasswordHash=get_password_hash("123456"),
    FullName="BS.CKI Phạm Quốc Duy",
    Phone="0911223344",
    Email="duy.pham@clinic.com",
    Role="DOCTOR",
)
db.add(user_doc)
db.commit()

doc = Doctor(UserID=user_doc.UserID, SpecialtyID=1, LicenseNumber="CCHN-12345/HCM")
db.add(doc)
db.commit()

# 2. Tạo User & Patient mẫu
user_pat1 = User(
    Username="lan_tran",
    PasswordHash=get_password_hash("123"),
    FullName="Trần Thị Lan",
    Phone="0901234567",
    Role="PATIENT",
)
user_pat2 = User(
    Username="nam_le",
    PasswordHash=get_password_hash("123"),
    FullName="Lê Hoàng Nam",
    Phone="0912345678",
    Role="PATIENT",
)
db.add_all([user_pat1, user_pat2])
db.commit()

p1 = Patient(
    UserID=user_pat1.UserID,
    DateOfBirth=date(1995, 5, 12),
    Gender="Nữ",
    Address="Quận 10, TP.HCM",
)
p2 = Patient(
    UserID=user_pat2.UserID,
    DateOfBirth=date(1988, 10, 20),
    Gender="Nam",
    Address="Bình Thạnh, TP.HCM",
)
db.add_all([p1, p2])
db.commit()

# 3. Tạo Appointment trạng thái CHECKED_IN
today = date.today()
a1 = Appointment(
    PatientID=p1.PatientID,
    DoctorID=doc.DoctorID,
    AppointmentDate=today,
    StartTime=time(8, 30),
    EndTime=time(9, 0),
    Reason="Sốt cao 3 ngày, ho có đờm",
    Status=AppointmentStatus.CHECKED_IN,
)
a2 = Appointment(
    PatientID=p2.PatientID,
    DoctorID=doc.DoctorID,
    AppointmentDate=today,
    StartTime=time(9, 0),
    EndTime=time(9, 30),
    Reason="Đau tức ngực, khó thở nhẹ",
    Status=AppointmentStatus.CHECKED_IN,
)
db.add_all([a1, a2])
db.commit()
db.close()
