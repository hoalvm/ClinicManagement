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
    IsWalkIn BIT NOT NULL CONSTRAINT DF_Patients_IsWalkIn DEFAULT 0,

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

CREATE TABLE StaffClinicAssignments
(
    UserID INT NOT NULL,
    ClinicID INT NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CONSTRAINT PK_StaffClinicAssignments PRIMARY KEY (UserID, ClinicID),
    CONSTRAINT FK_StaffClinicAssignments_Users
        FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT FK_StaffClinicAssignments_Clinics
        FOREIGN KEY (ClinicID) REFERENCES Clinics(ClinicID)
);
GO

CREATE TABLE AuthSessions
(
    JtiHash CHAR(64) NOT NULL PRIMARY KEY,
    UserID INT NOT NULL,
    IssuedAt DATETIME2 NOT NULL,
    ExpiresAt DATETIME2 NOT NULL,
    RevokedAt DATETIME2,
    CONSTRAINT FK_AuthSessions_Users FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT CK_AuthSessions_Expiry CHECK (ExpiresAt > IssuedAt)
);
GO

CREATE INDEX IX_AuthSessions_UserRevoked ON AuthSessions (UserID, RevokedAt);
GO

CREATE TABLE AuditEvents
(
    EventID BIGINT IDENTITY(1,1) PRIMARY KEY,
    ActorUserID INT,
    ActorRole NVARCHAR(20),
    Action NVARCHAR(80) NOT NULL,
    EntityType NVARCHAR(50) NOT NULL,
    EntityID INT,
    ClinicID INT,
    OccurredAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    Outcome NVARCHAR(20) NOT NULL,
    RequestID CHAR(32),
    Details NVARCHAR(1000),
    CONSTRAINT FK_AuditEvents_Users FOREIGN KEY (ActorUserID) REFERENCES Users(UserID),
    CONSTRAINT FK_AuditEvents_Clinics FOREIGN KEY (ClinicID) REFERENCES Clinics(ClinicID)
);
GO

CREATE INDEX IX_AuditEvents_Entity ON AuditEvents (EntityType, EntityID, OccurredAt);
GO

CREATE OR ALTER TRIGGER dbo.TR_AuditEvents_AppendOnly
ON dbo.AuditEvents
INSTEAD OF UPDATE, DELETE
AS
BEGIN
    THROW 51000, 'AuditEvents is append-only.', 1;
END;
GO

CREATE TABLE ProductionProvenance
(
    ProvenanceID TINYINT NOT NULL PRIMARY KEY
        CONSTRAINT CK_ProductionProvenance_Singleton CHECK (ProvenanceID = 1),
    Origin NVARCHAR(30) NOT NULL
        CONSTRAINT CK_ProductionProvenance_Origin CHECK (Origin = N'EMPTY_DATABASE'),
    RecordedAt DATETIME2 NOT NULL
        CONSTRAINT DF_ProductionProvenance_RecordedAt DEFAULT SYSUTCDATETIME()
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

CREATE TABLE DoctorScheduleExceptions
(
    ExceptionID INT IDENTITY(1,1) PRIMARY KEY,
    DoctorID INT NOT NULL,
    ExceptionDate DATE NOT NULL,
    StartTime TIME,
    EndTime TIME,
    Reason NVARCHAR(255) NOT NULL,
    CreatedByUserID INT NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_DoctorScheduleExceptions_Doctors
        FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID),
    CONSTRAINT FK_DoctorScheduleExceptions_Users
        FOREIGN KEY (CreatedByUserID) REFERENCES Users(UserID),
    CONSTRAINT CK_DoctorScheduleExceptions_Time
        CHECK ((StartTime IS NULL AND EndTime IS NULL) OR
               (StartTime IS NOT NULL AND EndTime IS NOT NULL AND StartTime < EndTime))
);
GO

CREATE INDEX IX_DoctorScheduleExceptions_DoctorDate
    ON DoctorScheduleExceptions (DoctorID, ExceptionDate, IsActive);
GO

--Bảng Appointments
CREATE TABLE Appointments
(
    AppointmentID INT IDENTITY(1,1) PRIMARY KEY,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    ClinicID INT,
    SpecialtyID INT,
    AppointmentDate DATE NOT NULL,
    StartTime TIME NOT NULL,
    EndTime TIME NOT NULL,
    Reason NVARCHAR(500),
    QueueNumber NVARCHAR(10),
    CheckInAt DATETIME2,
    ClinicalContextLoadedAt DATETIME2,
    ClinicalContextLoadedByUserID INT,
    CheckInNote NVARCHAR(500),
    CancellationReason NVARCHAR(500),
    LastRescheduleReason NVARCHAR(500),
    NoShowAt DATETIME2,
    NoShowByUserID INT,
    NoShowReasonCode NVARCHAR(30),
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

    CONSTRAINT FK_Appointments_Specialties
        FOREIGN KEY (SpecialtyID)
        REFERENCES Specialties(SpecialtyID),

    CONSTRAINT FK_Appointments_NoShowBy
        FOREIGN KEY (NoShowByUserID)
        REFERENCES Users(UserID),

    CONSTRAINT FK_Appointments_ClinicalContextLoadedBy
        FOREIGN KEY (ClinicalContextLoadedByUserID)
        REFERENCES Users(UserID),

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
                'CANCELLED',
                'NO_SHOW'
            )
        ),

    CONSTRAINT CK_Appointments_Time
        CHECK (StartTime < EndTime),

    CONSTRAINT CK_Appointments_ClinicalContextMarker
        CHECK ((ClinicalContextLoadedAt IS NULL AND ClinicalContextLoadedByUserID IS NULL)
               OR (ClinicalContextLoadedAt IS NOT NULL AND ClinicalContextLoadedByUserID IS NOT NULL)),

    CONSTRAINT CK_Appointments_ClinicalContextAfterCheckIn
        CHECK (ClinicalContextLoadedAt IS NULL OR
               (CheckInAt IS NOT NULL AND ClinicalContextLoadedAt >= CheckInAt)),

    CONSTRAINT CK_Appointments_NoShow
        CHECK (Status <> 'NO_SHOW' OR
               (NoShowAt IS NOT NULL AND NoShowByUserID IS NOT NULL
                AND NoShowReasonCode = 'NO_ARRIVAL'))
);
GO

CREATE UNIQUE INDEX UX_Appointments_ClinicDateQueue
    ON Appointments (ClinicID, AppointmentDate, QueueNumber)
    WHERE ClinicID IS NOT NULL AND QueueNumber IS NOT NULL;
GO

--Bảng MedicalRecords
CREATE TABLE MedicalRecords
(
    MedicalRecordID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL UNIQUE,
    Symptoms NVARCHAR(1000),
    Diagnosis NVARCHAR(1000),
    Notes NVARCHAR(2000),
    LateEntryReason NVARCHAR(500),
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
CREATE TABLE ChargeCatalog
(
    ChargeID INT IDENTITY(1,1) PRIMARY KEY,
    Code NVARCHAR(50) NOT NULL UNIQUE,
    DisplayName NVARCHAR(200) NOT NULL,
    Category NVARCHAR(20) NOT NULL,
    SpecialtyID INT,
    UnitPrice DECIMAL(18,2) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    EffectiveFrom DATETIME2 NOT NULL DEFAULT GETDATE(),
    EffectiveTo DATETIME2,

    CONSTRAINT FK_ChargeCatalog_Specialties
        FOREIGN KEY (SpecialtyID) REFERENCES Specialties(SpecialtyID),
    CONSTRAINT CK_ChargeCatalog_Category
        CHECK (Category IN ('CONSULTATION', 'MEDICATION')),
    CONSTRAINT CK_ChargeCatalog_UnitPrice
        CHECK (UnitPrice > 0),
    CONSTRAINT CK_ChargeCatalog_Validity
        CHECK (EffectiveTo IS NULL OR EffectiveTo > EffectiveFrom),
    CONSTRAINT CK_ChargeCatalog_ConsultationSpecialty
        CHECK (Category <> 'CONSULTATION' OR SpecialtyID IS NOT NULL)
);
GO

CREATE UNIQUE INDEX UX_ChargeCatalog_ActiveConsultation
    ON ChargeCatalog (SpecialtyID)
    WHERE Category = 'CONSULTATION' AND IsActive = 1;
GO

CREATE TABLE InvoiceItems
(
    InvoiceItemID INT IDENTITY(1,1) PRIMARY KEY,
    InvoiceID INT NOT NULL,
    ChargeID INT,
    ItemName NVARCHAR(200) NOT NULL,
    Quantity INT NOT NULL DEFAULT 1,
    UnitPrice DECIMAL(18,2) NOT NULL,

    CONSTRAINT FK_InvoiceItems_Invoices
        FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID),

    CONSTRAINT FK_InvoiceItems_ChargeCatalog
        FOREIGN KEY (ChargeID)
        REFERENCES ChargeCatalog(ChargeID),

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
    AmountReceived DECIMAL(18,2),
    ChangeDue DECIMAL(18,2),
    RecordedByUserID INT,
    ExternalReference NVARCHAR(100),
    VerifiedAt DATETIME2,

    CONSTRAINT FK_Payments_Invoices
        FOREIGN KEY (InvoiceID)
        REFERENCES Invoices(InvoiceID),

    CONSTRAINT FK_Payments_RecordedBy
        FOREIGN KEY (RecordedByUserID)
        REFERENCES Users(UserID),

    CONSTRAINT CK_Payments_Amount
        CHECK (Amount > 0),

    CONSTRAINT CK_Payments_Method
        CHECK (PaymentMethod IN ('CASH', 'CARD', 'TRANSFER')),

    CONSTRAINT CK_Payments_Received
        CHECK (AmountReceived IS NULL OR AmountReceived >= Amount),

    CONSTRAINT CK_Payments_Change
        CHECK (ChangeDue IS NULL OR ChangeDue >= 0)
);
GO

CREATE UNIQUE INDEX UX_Payments_TransferReference
    ON Payments (ExternalReference)
    WHERE PaymentMethod = 'TRANSFER' AND ExternalReference IS NOT NULL;
GO
