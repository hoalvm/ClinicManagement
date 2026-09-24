CREATE DATABASE ClinicManagementDB;
GO

USE ClinicManagementDB;
GO

--Bảng Users
CREATE TABLE Users
(
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(255) NOT NULL,
    FullName NVARCHAR(100) NOT NULL,
    Phone NVARCHAR(15),
    Email NVARCHAR(100),
    Role NVARCHAR(20) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT CK_Users_Role
        CHECK (Role IN ('PATIENT', 'DOCTOR', 'STAFF', 'ADMIN'))
);
GO

--Bảng Patients
CREATE TABLE Patients
(
    PatientID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL UNIQUE,
    DateOfBirth DATE,
    Gender NVARCHAR(10),
    Address NVARCHAR(255),

    CONSTRAINT FK_Patients_Users
        FOREIGN KEY (UserID)
        REFERENCES Users(UserID)
);
GO

--Bảng Specialties
CREATE TABLE Specialties
(
    SpecialtyID INT IDENTITY(1,1) PRIMARY KEY,
    SpecialtyName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(255),
    IsActive BIT NOT NULL DEFAULT 1
);
GO

--Bảng Clinics 
CREATE TABLE Clinics
(
    ClinicID INT IDENTITY(1,1) PRIMARY KEY,
    ClinicName NVARCHAR(150) NOT NULL,
    Address NVARCHAR(255),
    Phone NVARCHAR(15),
    IsActive BIT NOT NULL DEFAULT 1
);
GO

-- Bảng Doctors
CREATE TABLE Doctors
(
    DoctorID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL UNIQUE,
    SpecialtyID INT NOT NULL,
    ClinicID INT,
    LicenseNumber NVARCHAR(50) UNIQUE,
    IsActive BIT NOT NULL DEFAULT 1,

    CONSTRAINT FK_Doctors_Users
        FOREIGN KEY (UserID)
        REFERENCES Users(UserID),

    CONSTRAINT FK_Doctors_Specialties
        FOREIGN KEY (SpecialtyID)
        REFERENCES Specialties(SpecialtyID),

    CONSTRAINT FK_Doctors_Clinics
        FOREIGN KEY (ClinicID)
        REFERENCES Clinics(ClinicID)
);
GO

--Bảng DoctorSchedules
CREATE TABLE DoctorSchedules
(
    ScheduleID INT IDENTITY(1,1) PRIMARY KEY,
    DoctorID INT NOT NULL,
    DayOfWeek TINYINT NOT NULL,
    StartTime TIME NOT NULL,
    EndTime TIME NOT NULL,
    SlotDuration INT NOT NULL DEFAULT 30,
    IsActive BIT NOT NULL DEFAULT 1,

    CONSTRAINT FK_DoctorSchedules_Doctors
        FOREIGN KEY (DoctorID)
        REFERENCES Doctors(DoctorID),

    CONSTRAINT CK_DoctorSchedules_DayOfWeek
        CHECK (DayOfWeek BETWEEN 1 AND 7),

    CONSTRAINT CK_DoctorSchedules_Time
        CHECK (StartTime < EndTime),

    CONSTRAINT CK_DoctorSchedules_SlotDuration
        CHECK (SlotDuration > 0)
);
GO

--Bảng Appointments
CREATE TABLE Appointments
(
    AppointmentID INT IDENTITY(1,1) PRIMARY KEY,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    ClinicID INT,
    AppointmentDate DATE NOT NULL,
    StartTime TIME NOT NULL,
    EndTime TIME NOT NULL,
    Reason NVARCHAR(500),
    Status NVARCHAR(20) NOT NULL DEFAULT 'PENDING',
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Appointments_Patients
        FOREIGN KEY (PatientID)
        REFERENCES Patients(PatientID),

    CONSTRAINT FK_Appointments_Doctors
        FOREIGN KEY (DoctorID)
        REFERENCES Doctors(DoctorID),

    CONSTRAINT FK_Appointments_Clinics
        FOREIGN KEY (ClinicID)
        REFERENCES Clinics(ClinicID),

    CONSTRAINT CK_Appointments_Status
        CHECK
        (
            Status IN
            (
                'PENDING',
                'CONFIRMED',
                'CHECKED_IN',
                'IN_PROGRESS',
                'COMPLETED',
                'CANCELLED'
            )
        ),

    CONSTRAINT CK_Appointments_Time
        CHECK (StartTime < EndTime)
);
GO

--Bảng MedicalRecords
CREATE TABLE MedicalRecords
(
    MedicalRecordID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL UNIQUE,
    Symptoms NVARCHAR(1000),
    Diagnosis NVARCHAR(1000),
    Notes NVARCHAR(2000),
    ExaminationDate DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_MedicalRecords_Appointments
        FOREIGN KEY (AppointmentID)
        REFERENCES Appointments(AppointmentID)
);
GO

--Bảng Prescriptions (Đơn thuốc)
CREATE TABLE Prescriptions
(
    PrescriptionID INT IDENTITY(1,1) PRIMARY KEY,
    MedicalRecordID INT NOT NULL UNIQUE,
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    CONSTRAINT FK_Prescriptions_MedicalRecords
        FOREIGN KEY (MedicalRecordID)
        REFERENCES MedicalRecords(MedicalRecordID)
);
GO

--Bảng PrescriptionItems (Các loại thuốc)
CREATE TABLE PrescriptionItems
(
    PrescriptionItemID INT IDENTITY(1,1) PRIMARY KEY,
    PrescriptionID INT NOT NULL,
    MedicineName NVARCHAR(150) NOT NULL,
    Quantity INT NOT NULL,
    Dosage NVARCHAR(255),
    Instructions NVARCHAR(500),

    CONSTRAINT FK_PrescriptionItems_Prescriptions
        FOREIGN KEY (PrescriptionID)
        REFERENCES Prescriptions(PrescriptionID),

    CONSTRAINT CK_PrescriptionItems_Quantity
        CHECK (Quantity > 0)
);
GO

--Bảng Invoices (Hóa đơn)
CREATE TABLE Invoices
(
    InvoiceID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL UNIQUE,
    TotalAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    Status NVARCHAR(20) NOT NULL DEFAULT 'UNPAID',
    CreatedAt DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Invoices_Appointments
        FOREIGN KEY (AppointmentID)
        REFERENCES Appointments(AppointmentID),

    CONSTRAINT CK_Invoices_TotalAmount
        CHECK (TotalAmount >= 0),

    CONSTRAINT CK_Invoices_Status
        CHECK (Status IN ('UNPAID', 'PAID'))
);
GO

--Bảng InvoiceItems
CREATE TABLE InvoiceItems
(
    InvoiceItemID INT IDENTITY(1,1) PRIMARY KEY,
    InvoiceID INT NOT NULL,
    ItemName NVARCHAR(200) NOT NULL,
    Quantity INT NOT NULL DEFAULT 1,
    UnitPrice DECIMAL(18,2) NOT NULL,

    CONSTRAINT FK_InvoiceItems_Invoices
        FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID),

    CONSTRAINT CK_InvoiceItems_Quantity
        CHECK (Quantity > 0),

    CONSTRAINT CK_InvoiceItems_UnitPrice
        CHECK (UnitPrice >= 0)
);
GO

--Bảng Payments
CREATE TABLE Payments
(
    PaymentID INT IDENTITY(1,1) PRIMARY KEY,
    InvoiceID INT NOT NULL UNIQUE,
    Amount DECIMAL(18,2) NOT NULL,
    PaymentMethod NVARCHAR(20) NOT NULL,
    PaymentDate DATETIME2 NOT NULL DEFAULT GETDATE(),

    CONSTRAINT FK_Payments_Invoices
        FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID),

    CONSTRAINT CK_Payments_Amount
        CHECK (Amount > 0),

    CONSTRAINT CK_Payments_Method
        CHECK (PaymentMethod IN ('CASH', 'CARD'))
);
GO