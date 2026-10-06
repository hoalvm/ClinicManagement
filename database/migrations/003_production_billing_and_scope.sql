-- Preserve existing encounters and receipts while adding production provenance.
-- Historical InvoiceItems.ChargeID and Payments audit fields intentionally stay NULL.

IF OBJECT_ID(N'dbo.StaffClinicAssignments', N'U') IS NULL
    CREATE TABLE dbo.StaffClinicAssignments (
        UserID INT NOT NULL,
        ClinicID INT NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_StaffClinicAssignments_IsActive DEFAULT 1,
        CONSTRAINT PK_StaffClinicAssignments PRIMARY KEY (UserID, ClinicID),
        CONSTRAINT FK_StaffClinicAssignments_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID),
        CONSTRAINT FK_StaffClinicAssignments_Clinics FOREIGN KEY (ClinicID) REFERENCES dbo.Clinics(ClinicID)
    );
GO

IF OBJECT_ID(N'dbo.AuthSessions', N'U') IS NULL
    CREATE TABLE dbo.AuthSessions (
        JtiHash CHAR(64) NOT NULL PRIMARY KEY,
        UserID INT NOT NULL,
        IssuedAt DATETIME2 NOT NULL,
        ExpiresAt DATETIME2 NOT NULL,
        RevokedAt DATETIME2 NULL,
        CONSTRAINT FK_AuthSessions_Users FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID),
        CONSTRAINT CK_AuthSessions_Expiry CHECK (ExpiresAt > IssuedAt)
    );
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.AuthSessions')
      AND name = N'IX_AuthSessions_UserRevoked'
)
    CREATE INDEX IX_AuthSessions_UserRevoked ON dbo.AuthSessions (UserID, RevokedAt);
GO

IF OBJECT_ID(N'dbo.AuditEvents', N'U') IS NULL
    CREATE TABLE dbo.AuditEvents (
        EventID BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        ActorUserID INT NULL,
        ActorRole NVARCHAR(20) NULL,
        Action NVARCHAR(80) NOT NULL,
        EntityType NVARCHAR(50) NOT NULL,
        EntityID INT NULL,
        ClinicID INT NULL,
        OccurredAt DATETIME2 NOT NULL CONSTRAINT DF_AuditEvents_OccurredAt DEFAULT SYSUTCDATETIME(),
        Outcome NVARCHAR(20) NOT NULL,
        RequestID CHAR(32) NULL,
        Details NVARCHAR(1000) NULL,
        CONSTRAINT FK_AuditEvents_Users FOREIGN KEY (ActorUserID) REFERENCES dbo.Users(UserID),
        CONSTRAINT FK_AuditEvents_Clinics FOREIGN KEY (ClinicID) REFERENCES dbo.Clinics(ClinicID)
    );
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.AuditEvents')
      AND name = N'IX_AuditEvents_Entity'
)
    CREATE INDEX IX_AuditEvents_Entity ON dbo.AuditEvents (EntityType, EntityID, OccurredAt);
GO

IF OBJECT_ID(N'dbo.DoctorScheduleExceptions', N'U') IS NULL
    CREATE TABLE dbo.DoctorScheduleExceptions (
        ExceptionID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        DoctorID INT NOT NULL,
        ExceptionDate DATE NOT NULL,
        StartTime TIME NULL,
        EndTime TIME NULL,
        Reason NVARCHAR(255) NOT NULL,
        CreatedByUserID INT NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_DoctorScheduleExceptions_IsActive DEFAULT 1,
        CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_DoctorScheduleExceptions_CreatedAt DEFAULT SYSUTCDATETIME(),
        CONSTRAINT FK_DoctorScheduleExceptions_Doctors FOREIGN KEY (DoctorID) REFERENCES dbo.Doctors(DoctorID),
        CONSTRAINT FK_DoctorScheduleExceptions_Users FOREIGN KEY (CreatedByUserID) REFERENCES dbo.Users(UserID),
        CONSTRAINT CK_DoctorScheduleExceptions_Time
            CHECK ((StartTime IS NULL AND EndTime IS NULL) OR
                   (StartTime IS NOT NULL AND EndTime IS NOT NULL AND StartTime < EndTime))
    );
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.DoctorScheduleExceptions')
      AND name = N'IX_DoctorScheduleExceptions_DoctorDate'
)
    CREATE INDEX IX_DoctorScheduleExceptions_DoctorDate
        ON dbo.DoctorScheduleExceptions (DoctorID, ExceptionDate, IsActive);
GO

IF COL_LENGTH('dbo.Appointments', 'SpecialtyID') IS NULL
    ALTER TABLE dbo.Appointments ADD SpecialtyID INT NULL;
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID(N'dbo.Appointments')
      AND name = N'FK_Appointments_Specialties'
)
    ALTER TABLE dbo.Appointments ADD CONSTRAINT FK_Appointments_Specialties
        FOREIGN KEY (SpecialtyID) REFERENCES dbo.Specialties(SpecialtyID);
GO

-- Do not infer a historical encounter's specialty from the doctor's current
-- assignment: the doctor may have changed specialty since that visit. Legacy
-- rows remain NULL until an authorized, evidence-backed reconciliation.
-- Production preflight refuses unresolved appointments.

IF COL_LENGTH('dbo.Appointments', 'NoShowAt') IS NULL
    ALTER TABLE dbo.Appointments ADD NoShowAt DATETIME2 NULL;
IF COL_LENGTH('dbo.Appointments', 'NoShowByUserID') IS NULL
    ALTER TABLE dbo.Appointments ADD NoShowByUserID INT NULL;
IF COL_LENGTH('dbo.Appointments', 'NoShowReasonCode') IS NULL
    ALTER TABLE dbo.Appointments ADD NoShowReasonCode NVARCHAR(30) NULL;
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID(N'dbo.Appointments')
      AND name = N'FK_Appointments_NoShowBy'
)
    ALTER TABLE dbo.Appointments ADD CONSTRAINT FK_Appointments_NoShowBy
        FOREIGN KEY (NoShowByUserID) REFERENCES dbo.Users(UserID);
GO

IF EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Appointments')
      AND name = N'CK_Appointments_Status'
)
    ALTER TABLE dbo.Appointments DROP CONSTRAINT CK_Appointments_Status;
ALTER TABLE dbo.Appointments ADD CONSTRAINT CK_Appointments_Status
    CHECK (Status IN (
        'PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_PROGRESS',
        'COMPLETED', 'CANCELLED', 'NO_SHOW'
    ));
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Appointments')
      AND name = N'CK_Appointments_NoShow'
)
    ALTER TABLE dbo.Appointments ADD CONSTRAINT CK_Appointments_NoShow
        CHECK (Status <> 'NO_SHOW' OR
               (NoShowAt IS NOT NULL AND NoShowByUserID IS NOT NULL
                AND NoShowReasonCode = 'NO_ARRIVAL'));
GO

IF OBJECT_ID(N'dbo.ChargeCatalog', N'U') IS NULL
    CREATE TABLE dbo.ChargeCatalog (
        ChargeID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        Code NVARCHAR(50) NOT NULL UNIQUE,
        DisplayName NVARCHAR(200) NOT NULL,
        Category NVARCHAR(20) NOT NULL,
        SpecialtyID INT NULL,
        UnitPrice DECIMAL(18,2) NOT NULL,
        IsActive BIT NOT NULL CONSTRAINT DF_ChargeCatalog_IsActive DEFAULT 1,
        EffectiveFrom DATETIME2 NOT NULL CONSTRAINT DF_ChargeCatalog_EffectiveFrom DEFAULT GETDATE(),
        EffectiveTo DATETIME2 NULL,
        CONSTRAINT FK_ChargeCatalog_Specialties FOREIGN KEY (SpecialtyID) REFERENCES dbo.Specialties(SpecialtyID),
        CONSTRAINT CK_ChargeCatalog_Category CHECK (Category IN ('CONSULTATION', 'MEDICATION')),
        CONSTRAINT CK_ChargeCatalog_UnitPrice CHECK (UnitPrice > 0),
        CONSTRAINT CK_ChargeCatalog_Validity CHECK (EffectiveTo IS NULL OR EffectiveTo > EffectiveFrom),
        CONSTRAINT CK_ChargeCatalog_ConsultationSpecialty
            CHECK (Category <> 'CONSULTATION' OR SpecialtyID IS NOT NULL)
    );
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.ChargeCatalog')
      AND name = N'UX_ChargeCatalog_ActiveConsultation'
)
    CREATE UNIQUE INDEX UX_ChargeCatalog_ActiveConsultation
        ON dbo.ChargeCatalog (SpecialtyID)
        WHERE Category = 'CONSULTATION' AND IsActive = 1;
GO

IF COL_LENGTH('dbo.InvoiceItems', 'ChargeID') IS NULL
    ALTER TABLE dbo.InvoiceItems ADD ChargeID INT NULL;
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID(N'dbo.InvoiceItems')
      AND name = N'FK_InvoiceItems_ChargeCatalog'
)
    ALTER TABLE dbo.InvoiceItems ADD CONSTRAINT FK_InvoiceItems_ChargeCatalog
        FOREIGN KEY (ChargeID) REFERENCES dbo.ChargeCatalog(ChargeID);
GO

IF COL_LENGTH('dbo.Payments', 'AmountReceived') IS NULL
    ALTER TABLE dbo.Payments ADD AmountReceived DECIMAL(18,2) NULL;
IF COL_LENGTH('dbo.Payments', 'ChangeDue') IS NULL
    ALTER TABLE dbo.Payments ADD ChangeDue DECIMAL(18,2) NULL;
IF COL_LENGTH('dbo.Payments', 'RecordedByUserID') IS NULL
    ALTER TABLE dbo.Payments ADD RecordedByUserID INT NULL;
IF COL_LENGTH('dbo.Payments', 'ExternalReference') IS NULL
    ALTER TABLE dbo.Payments ADD ExternalReference NVARCHAR(100) NULL;
IF COL_LENGTH('dbo.Payments', 'VerifiedAt') IS NULL
    ALTER TABLE dbo.Payments ADD VerifiedAt DATETIME2 NULL;
IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE parent_object_id = OBJECT_ID(N'dbo.Payments')
      AND name = N'FK_Payments_RecordedBy'
)
    ALTER TABLE dbo.Payments ADD CONSTRAINT FK_Payments_RecordedBy
        FOREIGN KEY (RecordedByUserID) REFERENCES dbo.Users(UserID);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Payments')
      AND name = N'CK_Payments_Received'
)
    ALTER TABLE dbo.Payments ADD CONSTRAINT CK_Payments_Received
        CHECK (AmountReceived IS NULL OR AmountReceived >= Amount);
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE parent_object_id = OBJECT_ID(N'dbo.Payments')
      AND name = N'CK_Payments_Change'
)
    ALTER TABLE dbo.Payments ADD CONSTRAINT CK_Payments_Change
        CHECK (ChangeDue IS NULL OR ChangeDue >= 0);
IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'dbo.Payments')
      AND name = N'UX_Payments_TransferReference'
)
    CREATE UNIQUE INDEX UX_Payments_TransferReference
        ON dbo.Payments (ExternalReference)
        WHERE PaymentMethod = 'TRANSFER' AND ExternalReference IS NOT NULL;
GO
