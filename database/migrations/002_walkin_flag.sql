-- Distinguish intentionally login-disabled walk-ins from disabled patient accounts.
-- Existing patients remain registered patients unless explicitly created as walk-ins.
IF COL_LENGTH('dbo.Patients', 'IsWalkIn') IS NULL
    ALTER TABLE dbo.Patients ADD IsWalkIn BIT NOT NULL
        CONSTRAINT DF_Patients_IsWalkIn DEFAULT 0 WITH VALUES;
GO
