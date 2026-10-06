-- A clinician must successfully review the encounter's available history
-- after check-in before completing a production consultation. Existing rows
-- intentionally remain NULL and require a fresh review.
IF COL_LENGTH('dbo.Appointments', 'ClinicalContextLoadedAt') IS NULL
    ALTER TABLE dbo.Appointments ADD ClinicalContextLoadedAt DATETIME2 NULL;
GO

IF COL_LENGTH('dbo.Appointments', 'ClinicalContextLoadedByUserID') IS NULL
    ALTER TABLE dbo.Appointments ADD ClinicalContextLoadedByUserID INT NULL;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.foreign_keys
    WHERE name = 'FK_Appointments_ClinicalContextLoadedBy'
      AND parent_object_id = OBJECT_ID('dbo.Appointments')
)
    ALTER TABLE dbo.Appointments ADD CONSTRAINT FK_Appointments_ClinicalContextLoadedBy
        FOREIGN KEY (ClinicalContextLoadedByUserID) REFERENCES dbo.Users(UserID);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_Appointments_ClinicalContextMarker'
      AND parent_object_id = OBJECT_ID('dbo.Appointments')
)
    ALTER TABLE dbo.Appointments WITH CHECK ADD CONSTRAINT CK_Appointments_ClinicalContextMarker
        CHECK ((ClinicalContextLoadedAt IS NULL AND ClinicalContextLoadedByUserID IS NULL)
            OR (ClinicalContextLoadedAt IS NOT NULL AND ClinicalContextLoadedByUserID IS NOT NULL));
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints
    WHERE name = 'CK_Appointments_ClinicalContextAfterCheckIn'
      AND parent_object_id = OBJECT_ID('dbo.Appointments')
)
    ALTER TABLE dbo.Appointments WITH CHECK ADD CONSTRAINT CK_Appointments_ClinicalContextAfterCheckIn
        CHECK (ClinicalContextLoadedAt IS NULL OR
            (CheckInAt IS NOT NULL AND ClinicalContextLoadedAt >= CheckInAt));
GO
