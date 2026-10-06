-- Record only databases that were empty of clinic data when first provisioned.
-- Existing databases need a separately reviewed migration into a new clean
-- production database; never certify their contents by copying current doctor
-- attributes into historical encounters.
IF OBJECT_ID(N'dbo.ProductionProvenance', N'U') IS NULL
    CREATE TABLE dbo.ProductionProvenance (
        ProvenanceID TINYINT NOT NULL PRIMARY KEY
            CONSTRAINT CK_ProductionProvenance_Singleton CHECK (ProvenanceID = 1),
        Origin NVARCHAR(30) NOT NULL
            CONSTRAINT CK_ProductionProvenance_Origin CHECK (Origin = N'EMPTY_DATABASE'),
        RecordedAt DATETIME2 NOT NULL
            CONSTRAINT DF_ProductionProvenance_RecordedAt DEFAULT SYSUTCDATETIME()
    );
GO

IF NOT EXISTS (SELECT 1 FROM dbo.ProductionProvenance)
   AND NOT EXISTS (SELECT 1 FROM dbo.Users)
   AND NOT EXISTS (SELECT 1 FROM dbo.Patients)
   AND NOT EXISTS (SELECT 1 FROM dbo.Doctors)
   AND NOT EXISTS (SELECT 1 FROM dbo.Clinics)
   AND NOT EXISTS (SELECT 1 FROM dbo.Specialties)
   AND NOT EXISTS (SELECT 1 FROM dbo.Appointments)
   AND NOT EXISTS (SELECT 1 FROM dbo.MedicalRecords)
   AND NOT EXISTS (SELECT 1 FROM dbo.Invoices)
   AND NOT EXISTS (SELECT 1 FROM dbo.Payments)
   AND NOT EXISTS (
       SELECT 1 FROM dbo.SchemaMigrations WHERE MigrationID LIKE N'demo-seed-%'
   )
    INSERT INTO dbo.ProductionProvenance (ProvenanceID, Origin)
    VALUES (1, N'EMPTY_DATABASE');
GO
